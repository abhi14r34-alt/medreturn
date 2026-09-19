"""Household workflow: analyze, request pickup, track, credits, history."""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_household
from app.core.config import settings
from app.core.constants import (
    SUPPORTED_RETURN_CATEGORIES,
    Eligibility,
    PickupStatus,
)
from app.db.session import get_db
from app.ml import inference
from app.ml.decision import eligibility_for_return
from app.models import (
    Credit,
    CreditTransaction,
    HouseholdReturn,
    PickupRequest,
    User,
)
from app.schemas import (
    AnalysisOut,
    CreditsOut,
    CreditTransactionOut,
    HouseholdReturnOut,
    PickupCreateIn,
    PickupDetailOut,
    PickupOut,
    TrackingOut,
)
from app.services import maps, ocr, storage
from app.services.email import analysis_email
from app.services.ids import next_id
from app.services.pickups import transition

router = APIRouter(prefix="/household", tags=["household"])

ELIGIBILITY_MESSAGES = {
    Eligibility.ELIGIBLE.value: (
        "This looks like a supported return category. You can request a pickup."
    ),
    Eligibility.NEEDS_REVIEW.value: (
        "Confidence is below the threshold, so a person will check this item at "
        "collection. You can still request a pickup."
    ),
    Eligibility.UNSUPPORTED.value: (
        "This does not match a supported return category. Contact the helpline "
        "before arranging disposal."
    ),
}


@router.post("/analyze", response_model=AnalysisOut)
async def analyze(
    file: UploadFile = File(...),
    item_name: Optional[str] = Form(None),
    expiry_date: Optional[str] = Form(None),
    batch_number: Optional[str] = Form(None),
    user: User = Depends(require_household),
    db: Session = Depends(get_db),
) -> AnalysisOut:
    """Run one image through the analyzer and record the result.

    The response always reports inference_mode so the UI can label a
    simulated result as such. Analysis alone never earns credits.
    """
    path, data = await storage.save_image(file, "returns")

    ocr_result = ocr.read_image(data)
    item_name = item_name.strip() if item_name else None
    expiry_date = expiry_date.strip() if expiry_date else ocr_result.expiry_date
    batch_number = batch_number.strip() if batch_number else None
    # A fallback pool is used only when the explicit demo path is active. A
    # real model returns one of the labels stored in its own checkpoint.
    try:
        prediction = inference.predict(data, SUPPORTED_RETURN_CATEGORIES)
    except inference.InferenceUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    pool = inference.SUPPORTED_CLASSES if not prediction.is_demo else SUPPORTED_RETURN_CATEGORIES
    quality = inference.quality_status()

    # OCR supplies a descriptive item name, not a hard-coded category. The
    # model label remains the result produced by the trained checkpoint.
    identified_name = item_name or ocr.extract_item_name(ocr_result.text)
    detected_item = (
        f"{identified_name} — {prediction.label}"
        if identified_name else prediction.label
    )

    eligibility = eligibility_for_return(
        prediction.label,
        prediction.confidence,
        pool,
        manual_review_labels=settings.HUMAN_VERIFICATION_LABELS,
    )
    quality_requires_review = not prediction.is_demo and not quality["deployable"]
    if quality_requires_review:
        eligibility = Eligibility.NEEDS_REVIEW.value

    record = HouseholdReturn(
        user_id=user.id,
        image_path=path,
        item_name=identified_name,
        expiry_date=expiry_date,
        batch_number=batch_number,
        detected_item=detected_item,
        category=(
            prediction.label
            if eligibility != Eligibility.UNSUPPORTED.value
            else "Unknown"
        ),
        confidence=prediction.confidence,
        eligibility_status=eligibility,
        inference_mode=prediction.mode,
    )
    db.add(record)
    analysis_email(
        db,
        user,
        detected_item=detected_item,
        model_label=prediction.label,
        confidence=prediction.confidence,
        review_required=(eligibility != Eligibility.ELIGIBLE.value),
    )
    db.commit()
    db.refresh(record)

    return AnalysisOut(
        return_id=record.id,
        detected_item=record.detected_item,
        item_name=record.item_name,
        expiry_date=record.expiry_date,
        batch_number=record.batch_number,
        category=record.category,
        confidence=round(prediction.confidence, 4),
        confidence_threshold=settings.CONFIDENCE_THRESHOLD,
        eligibility_status=eligibility,
        inference_mode=prediction.mode,
        is_simulated=prediction.is_demo,
        model_version=prediction.model_version,
        ocr_text=ocr_result.text or None,
        ocr_available=ocr_result.available,
        human_verification_required=(eligibility != Eligibility.ELIGIBLE.value),
        model_quality=quality,
        message=ELIGIBILITY_MESSAGES.get(eligibility, "Analysis complete."),
        supported_categories=pool,
    )


@router.post("/pickups", response_model=PickupDetailOut,
             status_code=status.HTTP_201_CREATED)
def create_pickup(
    payload: PickupCreateIn,
    user: User = Depends(require_household),
    db: Session = Depends(get_db),
) -> PickupRequest:
    pickup = PickupRequest(
        pickup_id=next_id(db, "pickup"),
        user_id=user.id,
        address=payload.address.strip(),
        contact_phone=payload.contact_phone,
        latitude=payload.latitude,
        longitude=payload.longitude,
        preferred_date=payload.preferred_date,
        time_slot=payload.time_slot,
        item_count=payload.item_count,
        approx_weight_kg=payload.approx_weight_kg,
        notes=payload.notes,
        status=PickupStatus.REQUESTED.value,
    )
    db.add(pickup)
    db.flush()

    if payload.return_id is not None:
        item = db.get(HouseholdReturn, payload.return_id)
        if item is not None and item.user_id == user.id:
            item.pickup_id = pickup.pickup_id

    # Record the opening history row, notify and email.
    from app.services.email import pickup_email
    from app.services.pickups import notify
    from app.models import PickupStatusHistory

    db.add(PickupStatusHistory(
        pickup_request_id=pickup.id,
        status=PickupStatus.REQUESTED.value,
        changed_by=user.id,
    ))
    notify(db, user.id, "Pickup requested",
           f"We received {pickup.pickup_id}. A slot confirmation follows shortly.")
    pickup_email(db, user, pickup, PickupStatus.REQUESTED)

    db.commit()
    db.refresh(pickup)
    return pickup


@router.get("/pickups", response_model=List[PickupOut])
def list_pickups(
    user: User = Depends(require_household),
    db: Session = Depends(get_db),
) -> List[PickupRequest]:
    return db.execute(
        select(PickupRequest)
        .where(PickupRequest.user_id == user.id)
        .order_by(desc(PickupRequest.created_at))
    ).scalars().all()


def _owned_pickup(db: Session, user: User, pickup_id: str) -> PickupRequest:
    pickup = db.execute(
        select(PickupRequest).where(PickupRequest.pickup_id == pickup_id)
    ).scalar_one_or_none()
    if pickup is None or pickup.user_id != user.id:
        # 404 rather than 403, so the endpoint does not confirm that a
        # pickup belonging to someone else exists.
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pickup not found.")
    return pickup


@router.get("/pickups/{pickup_id}", response_model=PickupDetailOut)
def get_pickup(
    pickup_id: str,
    user: User = Depends(require_household),
    db: Session = Depends(get_db),
) -> PickupRequest:
    return _owned_pickup(db, user, pickup_id)


@router.get("/pickups/{pickup_id}/tracking", response_model=TrackingOut)
def track_pickup(
    pickup_id: str,
    user: User = Depends(require_household),
    db: Session = Depends(get_db),
) -> TrackingOut:
    pickup = _owned_pickup(db, user, pickup_id)
    snapshot = maps.get_provider().track(pickup)
    return TrackingOut(
        pickup_id=pickup.pickup_id,
        status=pickup.status,
        demo=snapshot.demo,
        collector_lat=snapshot.collector_lat,
        collector_lng=snapshot.collector_lng,
        destination_lat=snapshot.destination_lat,
        destination_lng=snapshot.destination_lng,
        eta_minutes=snapshot.eta_minutes,
        distance_km=snapshot.distance_km,
        note=snapshot.note,
    )


@router.post("/pickups/{pickup_id}/cancel", response_model=PickupDetailOut)
def cancel_pickup(
    pickup_id: str,
    user: User = Depends(require_household),
    db: Session = Depends(get_db),
) -> PickupRequest:
    pickup = _owned_pickup(db, user, pickup_id)
    if pickup.status not in (PickupStatus.REQUESTED.value,
                             PickupStatus.SCHEDULED.value):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="A collector is already on this job. Call the helpline to cancel.",
        )
    transition(db, pickup, PickupStatus.CANCELLED, actor=user)
    db.commit()
    db.refresh(pickup)
    return pickup


@router.get("/credits", response_model=CreditsOut)
def get_credits(
    user: User = Depends(require_household),
    db: Session = Depends(get_db),
) -> CreditsOut:
    wallet = db.execute(
        select(Credit).where(Credit.user_id == user.id)
    ).scalar_one_or_none()

    # Pending = collected or verified but not yet paid out.
    pending_count = db.execute(
        select(func.count(PickupRequest.id)).where(
            PickupRequest.user_id == user.id,
            PickupRequest.status.in_([
                PickupStatus.COLLECTED.value,
                PickupStatus.VERIFIED.value,
            ]),
        )
    ).scalar_one()

    return CreditsOut(
        balance=wallet.balance if wallet else 0,
        lifetime_earned=wallet.lifetime_earned if wallet else 0,
        pending=pending_count * settings.CREDITS_PER_VERIFIED_RETURN,
        credits_per_verified_return=settings.CREDITS_PER_VERIFIED_RETURN,
    )


@router.get("/credits/transactions", response_model=List[CreditTransactionOut])
def credit_transactions(
    user: User = Depends(require_household),
    db: Session = Depends(get_db),
) -> List[CreditTransaction]:
    return db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user.id)
        .order_by(desc(CreditTransaction.created_at))
    ).scalars().all()


@router.get("/history", response_model=List[HouseholdReturnOut])
def history(
    user: User = Depends(require_household),
    db: Session = Depends(get_db),
    eligibility: Optional[str] = None,
) -> List[HouseholdReturn]:
    query = select(HouseholdReturn).where(HouseholdReturn.user_id == user.id)
    if eligibility:
        query = query.where(HouseholdReturn.eligibility_status == eligibility)
    return db.execute(
        query.order_by(desc(HouseholdReturn.created_at))
    ).scalars().all()
