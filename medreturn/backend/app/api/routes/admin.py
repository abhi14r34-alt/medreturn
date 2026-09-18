"""Admin console endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import settings
from app.core.constants import (
    SUPPORTED_RETURN_CATEGORIES,
    SUPPORTED_WASTE_CLASSES,
    Decision,
    PickupStatus,
    QuarantineStatus,
)
from app.db.session import get_db
from app.ml import inference
from app.models import (
    Collector,
    CreditTransaction,
    EmailLog,
    Hospital,
    HouseholdReturn,
    ModelVersion,
    PickupRequest,
    QuarantineEvent,
    User,
    WasteEvent,
)
from app.schemas import (
    AdminDashboardOut,
    AssignCollectorIn,
    CollectorOut,
    CreditTransactionOut,
    HospitalOut,
    ModelInfoOut,
    PickupDetailOut,
    SettingsOut,
    StatusUpdateIn,
    UserOut,
)
from app.services import hardware
from app.services.pickups import transition

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardOut)
def dashboard(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminDashboardOut:
    pickups = db.execute(select(PickupRequest)).scalars().all()
    waste = db.execute(select(WasteEvent)).scalars().all()
    completed = [p for p in pickups if p.status == PickupStatus.COMPLETED.value]

    distribution: dict = {}
    for event in waste:
        distribution[event.predicted_class] = distribution.get(event.predicted_class, 0) + 1

    by_status: dict = {}
    for pickup in pickups:
        by_status[pickup.status] = by_status.get(pickup.status, 0) + 1

    credits_total = db.execute(
        select(func.coalesce(func.sum(CreditTransaction.amount), 0))
    ).scalar_one()

    open_quarantine = db.execute(
        select(func.count(QuarantineEvent.id)).where(
            QuarantineEvent.status == QuarantineStatus.QUARANTINED.value
        )
    ).scalar_one()

    return AdminDashboardOut(
        household_returns=db.execute(
            select(func.count(HouseholdReturn.id))
        ).scalar_one(),
        waste_events=len(waste),
        quarantined_open=open_quarantine,
        pickups_total=len(pickups),
        pickups_completed=len(completed),
        completion_rate=(
            round(len(completed) / len(pickups) * 100, 1) if pickups else 0.0
        ),
        credits_distributed=int(credits_total),
        average_confidence=(
            round(sum(e.confidence for e in waste) / len(waste), 4) if waste else None
        ),
        category_distribution=distribution,
        pickups_by_status=by_status,
    )


# ----------------------------------------------------------- pickups
@router.get("/pickups", response_model=List[PickupDetailOut])
def list_pickups(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = None,
    limit: int = 200,
) -> List[PickupRequest]:
    query = select(PickupRequest)
    if status_filter:
        query = query.where(PickupRequest.status == status_filter)
    return db.execute(
        query.order_by(desc(PickupRequest.created_at)).limit(min(limit, 500))
    ).scalars().all()


def _get_pickup(db: Session, pickup_id: str) -> PickupRequest:
    pickup = db.execute(
        select(PickupRequest).where(PickupRequest.pickup_id == pickup_id)
    ).scalar_one_or_none()
    if pickup is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pickup not found.")
    return pickup


@router.patch("/pickups/{pickup_id}/status", response_model=PickupDetailOut)
def update_status(
    pickup_id: str,
    payload: StatusUpdateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PickupRequest:
    """Advance a pickup one stage.

    Credits are created by the CREDITS_AWARDED transition and nowhere else,
    which is only reachable after COLLECTED and VERIFIED have been recorded.
    """
    pickup = _get_pickup(db, pickup_id)
    transition(db, pickup, payload.status, actor=admin, note=payload.note)
    db.commit()
    db.refresh(pickup)
    return pickup


@router.post("/pickups/{pickup_id}/assign", response_model=PickupDetailOut)
def assign_collector(
    pickup_id: str,
    payload: AssignCollectorIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PickupRequest:
    pickup = _get_pickup(db, pickup_id)
    collector = db.get(Collector, payload.collector_id)
    if collector is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Collector not found.")

    pickup.collector_id = collector.id

    # Walk forward to ASSIGNED if we are behind it.
    order = [s.value for s in PickupStatus]
    from app.core.constants import PICKUP_FLOW

    current_index = PICKUP_FLOW.index(PickupStatus(pickup.status))
    target_index = PICKUP_FLOW.index(PickupStatus.ASSIGNED)
    while current_index < target_index:
        current_index += 1
        transition(db, pickup, PICKUP_FLOW[current_index], actor=admin,
                   note=f"Assigned to {collector.name}")

    db.commit()
    db.refresh(pickup)
    return pickup


@router.get("/collectors", response_model=List[CollectorOut])
def list_collectors(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[Collector]:
    return db.execute(select(Collector).order_by(Collector.name)).scalars().all()


# ------------------------------------------------------------- users
@router.get("/users", response_model=List[UserOut])
def list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    role: Optional[str] = None,
) -> List[User]:
    """Deliberately returns UserOut, which omits the home address."""
    query = select(User)
    if role:
        query = query.where(User.role == role)
    return db.execute(query.order_by(User.id)).scalars().all()


@router.patch("/users/{user_id}/active", response_model=UserOut)
def set_active(
    user_id: int,
    is_active: bool,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail="You cannot disable your own account.")
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------- hospitals
@router.get("/hospitals", response_model=List[HospitalOut])
def list_hospitals(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[Hospital]:
    return db.execute(select(Hospital).order_by(Hospital.name)).scalars().all()


@router.patch("/hospitals/{hospital_id}/status", response_model=HospitalOut)
def set_hospital_status(
    hospital_id: int,
    new_status: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Hospital:
    hospital = db.get(Hospital, hospital_id)
    if hospital is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Hospital not found.")
    if new_status not in {"ACTIVE", "PENDING", "SUSPENDED"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown status.")
    hospital.status = new_status
    db.commit()
    db.refresh(hospital)
    return hospital


# ----------------------------------------------------------- credits
@router.get("/credits/transactions", response_model=List[CreditTransactionOut])
def all_transactions(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = 200,
) -> List[CreditTransaction]:
    return db.execute(
        select(CreditTransaction)
        .order_by(desc(CreditTransaction.created_at))
        .limit(min(limit, 500))
    ).scalars().all()


# ------------------------------------------------------------ emails
@router.get("/emails")
def email_log(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = 100,
) -> list:
    rows = db.execute(
        select(EmailLog).order_by(desc(EmailLog.created_at)).limit(min(limit, 500))
    ).scalars().all()
    return [
        {
            "id": r.id,
            "recipient": r.recipient,
            "subject": r.subject,
            "pickup_id": r.pickup_id,
            "transport": r.transport,
            "delivered": r.delivered,
            "error": r.error,
            "created_at": r.created_at,
        }
        for r in rows
    ]


# ------------------------------------------------------------- model
@router.get("/model", response_model=ModelInfoOut)
def model_info(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ModelInfoOut:
    versions = db.execute(
        select(ModelVersion).order_by(desc(ModelVersion.created_at))
    ).scalars().all()
    return ModelInfoOut(runtime=inference.model_status(), versions=versions)


@router.post("/model/{version_id}/deploy", response_model=ModelInfoOut)
def deploy_version(
    version_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ModelInfoOut:
    """Mark a version as deployed.

    This records the intent. Actually serving those weights means pointing
    MODEL_PATH at the matching checkpoint and restarting the API, which is
    a deliberate, controlled step rather than an automatic one.
    """
    target = db.get(ModelVersion, version_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Model version not found.")

    for version in db.execute(select(ModelVersion)).scalars().all():
        version.status = "ARCHIVED"
    target.status = "DEPLOYED"
    db.commit()

    versions = db.execute(
        select(ModelVersion).order_by(desc(ModelVersion.created_at))
    ).scalars().all()
    return ModelInfoOut(runtime=inference.model_status(), versions=versions)


# ---------------------------------------------------------- settings
@router.get("/settings", response_model=SettingsOut)
def read_settings(_: User = Depends(require_admin)) -> SettingsOut:
    """Runtime configuration, read-only.

    These come from the environment on purpose. Changing the confidence
    threshold or the credit rate is a deployment action with an audit
    trail, not a click in a web form.
    """
    return SettingsOut(
        demo_mode=settings.DEMO_MODE,
        confidence_threshold=settings.CONFIDENCE_THRESHOLD,
        credits_per_verified_return=settings.CREDITS_PER_VERIFIED_RETURN,
        supported_waste_classes=SUPPORTED_WASTE_CLASSES,
        supported_return_categories=SUPPORTED_RETURN_CATEGORIES,
        email_transport="smtp" if settings.email_configured else "console",
        maps_provider=settings.MAPS_PROVIDER,
        hardware_simulated=hardware.get_controller().simulated,
    )
