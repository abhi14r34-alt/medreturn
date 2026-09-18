"""Hospital workflow: predict, events, traceability, quarantine, bins."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_hospital
from app.core.config import settings
from app.core.constants import (
    SUPPORTED_WASTE_CLASSES,
    Decision,
    QuarantineStatus,
    Role,
)
from app.db.session import get_db
from app.ml import inference
from app.ml.decision import route_waste
from app.models import ModelVersion, QuarantineEvent, User, WasteEvent
from app.schemas import (
    ModelInfoOut,
    QuarantineOut,
    QuarantineVerifyIn,
    WasteEventOut,
    WastePredictionOut,
)
from app.services import hardware, storage
from app.services.ids import next_id

router = APIRouter(prefix="/hospital", tags=["hospital"])


def _scope(user: User) -> Optional[int]:
    """Hospital staff see only their own facility. Admins see everything."""
    return None if user.role == Role.ADMIN.value else user.hospital_id


def _require_hospital_id(user: User) -> int:
    if user.hospital_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="This account is not linked to a hospital. Ask an admin to set one.",
        )
    return user.hospital_id


@router.post("/predict", response_model=WastePredictionOut)
async def predict(
    file: UploadFile = File(...),
    weight_kg: float = Form(0.0),
    location: str = Form("Unspecified inlet"),
    user: User = Depends(require_hospital),
    db: Session = Depends(get_db),
) -> WastePredictionOut:
    """Classify one item, apply the confidence gate, log it, command the gate.

    An item is routed only when its class is supported and confidence clears
    the threshold. Everything else is quarantined and waits for a person.
    """
    hospital_id = _require_hospital_id(user)
    path, data = await storage.save_image(file, "waste")

    pool = inference.SUPPORTED_CLASSES or SUPPORTED_WASTE_CLASSES

    try:
        prediction = inference.predict(data, pool)
    except inference.InferenceUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    routing = route_waste(prediction.label, prediction.confidence, pool)

    event = WasteEvent(
        event_id=next_id(db, "waste"),
        hospital_id=hospital_id,
        operator_id=user.id,
        predicted_class=prediction.label,
        confidence=prediction.confidence,
        weight_kg=weight_kg,
        location=location,
        image_path=path,
        decision=routing.decision,
        route=routing.route,
        reason=routing.reason,
        model_version=prediction.model_version,
        inference_mode=prediction.mode,
    )
    db.add(event)
    db.flush()

    if routing.decision == Decision.QUARANTINED.value:
        db.add(QuarantineEvent(
            quarantine_id=next_id(db, "quarantine"),
            waste_event_id=event.id,
            reason=routing.reason,
            status=QuarantineStatus.QUARANTINED.value,
        ))

    command = hardware.get_controller().send(event.event_id, routing.route)
    db.commit()

    return WastePredictionOut(
        event_id=event.event_id,
        predicted_class=prediction.label,
        confidence=round(prediction.confidence, 4),
        confidence_threshold=settings.CONFIDENCE_THRESHOLD,
        decision=routing.decision,
        route=routing.route,
        reason=routing.reason,
        weight_kg=weight_kg,
        location=location,
        inference_mode=prediction.mode,
        is_simulated=prediction.is_demo,
        model_version=prediction.model_version,
        hardware_simulated=command.simulated,
        hardware_detail=command.detail,
        supported_classes=pool,
    )


@router.get("/events", response_model=List[WasteEventOut])
def events(
    user: User = Depends(require_hospital),
    db: Session = Depends(get_db),
    decision: Optional[str] = None,
    predicted_class: Optional[str] = None,
    location: Optional[str] = None,
    min_confidence: Optional[float] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 200,
) -> List[WasteEvent]:
    """Traceability search. Every filter in the spec is supported here."""
    query = select(WasteEvent)

    scope = _scope(user)
    if scope is not None:
        query = query.where(WasteEvent.hospital_id == scope)
    if decision:
        query = query.where(WasteEvent.decision == decision)
    if predicted_class:
        query = query.where(WasteEvent.predicted_class == predicted_class)
    if location:
        query = query.where(WasteEvent.location.like(f"%{location}%"))
    if min_confidence is not None:
        query = query.where(WasteEvent.confidence >= min_confidence)
    if date_from:
        query = query.where(WasteEvent.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.where(WasteEvent.created_at <= datetime.fromisoformat(date_to))

    return db.execute(
        query.order_by(desc(WasteEvent.created_at)).limit(min(limit, 500))
    ).scalars().all()


@router.get("/dashboard")
def dashboard(
    user: User = Depends(require_hospital),
    db: Session = Depends(get_db),
) -> dict:
    scope = _scope(user)
    base = select(WasteEvent)
    if scope is not None:
        base = base.where(WasteEvent.hospital_id == scope)

    rows = db.execute(base).scalars().all()
    accepted = [e for e in rows if e.decision == Decision.ACCEPTED.value]
    quarantined = [e for e in rows if e.decision == Decision.QUARANTINED.value]

    by_class: dict = {}
    for event in rows:
        by_class[event.predicted_class] = by_class.get(event.predicted_class, 0) + 1

    daily: dict = {}
    for event in rows:
        key = event.created_at.date().isoformat()
        daily[key] = daily.get(key, 0) + 1

    return {
        "total_analyzed": len(rows),
        "accepted": len(accepted),
        "quarantined": len(quarantined),
        "average_confidence": (
            round(sum(e.confidence for e in rows) / len(rows), 4) if rows else None
        ),
        "total_weight_kg": round(sum(e.weight_kg or 0 for e in rows), 2),
        "category_distribution": by_class,
        "daily_counts": dict(sorted(daily.items())),
        "demo_mode": inference.model_status()["mode"] == "DEMO",
    }


@router.get("/bins")
def bins(
    user: User = Depends(require_hospital),
    db: Session = Depends(get_db),
    capacity_kg: float = 14.0,
) -> dict:
    """Fill levels derived from accepted weights.

    This is an estimate from logged events, not a sensor reading. Wire a
    real load cell in and replace this calculation.
    """
    scope = _scope(user)
    query = select(WasteEvent).where(WasteEvent.decision == Decision.ACCEPTED.value)
    if scope is not None:
        query = query.where(WasteEvent.hospital_id == scope)
    rows = db.execute(query).scalars().all()

    compartments = []
    for index, name in enumerate(SUPPORTED_WASTE_CLASSES):
        weight = sum(e.weight_kg or 0 for e in rows if e.predicted_class == name)
        compartments.append({
            "name": name,
            "compartment": f"COMPARTMENT {chr(ord('A') + index)}",
            "weight_kg": round(weight, 2),
            "capacity_kg": capacity_kg,
            "fill_percent": min(100, round(weight / capacity_kg * 100)),
        })

    return {
        "compartments": compartments,
        "sensor_connected": False,
        "note": "Estimated from logged event weights, not a live sensor feed.",
    }


@router.get("/quarantine", response_model=List[QuarantineOut])
def quarantine_queue(
    user: User = Depends(require_hospital),
    db: Session = Depends(get_db),
    open_only: bool = True,
) -> List[QuarantineOut]:
    query = select(QuarantineEvent).join(WasteEvent)
    scope = _scope(user)
    if scope is not None:
        query = query.where(WasteEvent.hospital_id == scope)
    if open_only:
        query = query.where(QuarantineEvent.status == QuarantineStatus.QUARANTINED.value)

    records = db.execute(
        query.order_by(desc(QuarantineEvent.created_at))
    ).scalars().all()

    return [
        QuarantineOut(
            quarantine_id=q.quarantine_id,
            status=q.status,
            reason=q.reason,
            created_at=q.created_at,
            reviewed_at=q.reviewed_at,
            reviewer_note=q.reviewer_note,
            corrected_class=q.corrected_class,
            event=WasteEventOut.model_validate(q.event),
        )
        for q in records
    ]


@router.post("/quarantine/{quarantine_id}/verify", response_model=QuarantineOut)
def verify_quarantine(
    quarantine_id: str,
    payload: QuarantineVerifyIn,
    user: User = Depends(require_hospital),
    db: Session = Depends(get_db),
) -> QuarantineOut:
    """Record a human decision on a held item.

    An item is never released automatically; this endpoint is the only way
    out of quarantine, and the reviewer is recorded against it. The
    corrected class becomes a labelled example for a future training run,
    but it does not retrain anything by itself.
    """
    record = db.execute(
        select(QuarantineEvent).where(QuarantineEvent.quarantine_id == quarantine_id)
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Quarantine record not found.")

    scope = _scope(user)
    if scope is not None and record.event.hospital_id != scope:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Quarantine record not found.")
    if record.status != QuarantineStatus.QUARANTINED.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"This item was already reviewed ({record.status}).",
        )

    if payload.corrected_class and payload.corrected_class not in SUPPORTED_WASTE_CLASSES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Corrected class must be one of the configured supported classes.",
        )

    now = datetime.utcnow()
    record.status = (
        QuarantineStatus.VERIFIED_RELEASED.value
        if payload.release
        else QuarantineStatus.KEPT.value
    )
    record.reviewed_by = user.id
    record.reviewer_note = payload.note
    record.corrected_class = payload.corrected_class
    record.reviewed_at = now

    event = record.event
    event.verification_status = record.status
    event.verified_by = user.id
    event.verified_at = now

    if payload.release:
        final_class = payload.corrected_class or event.predicted_class
        if final_class in SUPPORTED_WASTE_CLASSES:
            index = SUPPORTED_WASTE_CLASSES.index(final_class)
            event.route = f"COMPARTMENT {chr(ord('A') + index)}"
            hardware.get_controller().send(event.event_id, event.route)

    db.commit()
    db.refresh(record)

    return QuarantineOut(
        quarantine_id=record.quarantine_id,
        status=record.status,
        reason=record.reason,
        created_at=record.created_at,
        reviewed_at=record.reviewed_at,
        reviewer_note=record.reviewer_note,
        corrected_class=record.corrected_class,
        event=WasteEventOut.model_validate(record.event),
    )


@router.get("/model", response_model=ModelInfoOut)
def model_info(
    user: User = Depends(require_hospital),
    db: Session = Depends(get_db),
) -> ModelInfoOut:
    versions = db.execute(
        select(ModelVersion).order_by(desc(ModelVersion.created_at))
    ).scalars().all()
    return ModelInfoOut(runtime=inference.model_status(), versions=versions)
