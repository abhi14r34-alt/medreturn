"""Collector interface: today's jobs and the field status buttons."""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_collector
from app.core.constants import PickupStatus
from app.db.session import get_db
from app.models import Collector, PickupRequest, User
from app.schemas import PickupDetailOut, StatusUpdateIn
from app.services import storage
from app.services.pickups import transition

router = APIRouter(prefix="/collector", tags=["collector"])

# The only transitions a collector may perform from the field.
FIELD_TRANSITIONS = {
    PickupStatus.ON_THE_WAY,
    PickupStatus.ARRIVED,
    PickupStatus.COLLECTED,
}


def _profile(db: Session, user: User) -> Collector:
    record = db.execute(
        select(Collector).where(Collector.user_id == user.id)
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="This login is not linked to a collector profile.",
        )
    return record


@router.get("/pickups", response_model=List[PickupDetailOut])
def my_pickups(
    user: User = Depends(require_collector),
    db: Session = Depends(get_db),
    today_only: bool = False,
) -> List[PickupRequest]:
    """Assigned jobs. The address is included because this collector needs
    it to do the job; no other household data is exposed."""
    me = _profile(db, user)
    query = select(PickupRequest).where(
        PickupRequest.collector_id == me.id,
        PickupRequest.status.in_([
            PickupStatus.ASSIGNED.value,
            PickupStatus.ON_THE_WAY.value,
            PickupStatus.ARRIVED.value,
        ]),
    )
    if today_only:
        query = query.where(PickupRequest.preferred_date == date.today().isoformat())
    return db.execute(query.order_by(PickupRequest.preferred_date)).scalars().all()


@router.get("/pickups/completed", response_model=List[PickupDetailOut])
def completed(
    user: User = Depends(require_collector),
    db: Session = Depends(get_db),
) -> List[PickupRequest]:
    me = _profile(db, user)
    return db.execute(
        select(PickupRequest).where(
            PickupRequest.collector_id == me.id,
            PickupRequest.status.in_([
                PickupStatus.COLLECTED.value,
                PickupStatus.VERIFIED.value,
                PickupStatus.CREDITS_AWARDED.value,
                PickupStatus.COMPLETED.value,
            ]),
        ).order_by(PickupRequest.collected_at.desc())
    ).scalars().all()


@router.patch("/pickups/{pickup_id}/status", response_model=PickupDetailOut)
def update_status(
    pickup_id: str,
    payload: StatusUpdateIn,
    user: User = Depends(require_collector),
    db: Session = Depends(get_db),
) -> PickupRequest:
    me = _profile(db, user)
    pickup = db.execute(
        select(PickupRequest).where(PickupRequest.pickup_id == pickup_id)
    ).scalar_one_or_none()
    if pickup is None or pickup.collector_id != me.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pickup not found.")

    if payload.status not in FIELD_TRANSITIONS:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=("Collectors may set ON_THE_WAY, ARRIVED or COLLECTED only. "
                    "Verification and credits are handled by operations."),
        )

    transition(db, pickup, payload.status, actor=user, note=payload.note)
    db.commit()
    db.refresh(pickup)
    return pickup


@router.post("/pickups/{pickup_id}/proof", response_model=PickupDetailOut)
async def upload_proof(
    pickup_id: str,
    file: UploadFile = File(...),
    user: User = Depends(require_collector),
    db: Session = Depends(get_db),
) -> PickupRequest:
    """Optional collection photo, attached after the items are taken."""
    me = _profile(db, user)
    pickup = db.execute(
        select(PickupRequest).where(PickupRequest.pickup_id == pickup_id)
    ).scalar_one_or_none()
    if pickup is None or pickup.collector_id != me.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pickup not found.")

    path, _data = await storage.save_image(file, "proof")
    pickup.proof_image_path = path
    db.commit()
    db.refresh(pickup)
    return pickup
