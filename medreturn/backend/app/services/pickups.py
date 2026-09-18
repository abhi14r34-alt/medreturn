"""Pickup lifecycle, notifications and credit awards.

All state changes funnel through transition(), which enforces the order of
the lifecycle, writes history, sends the email and creates the in-app
notification. Nothing else in the codebase mutates PickupRequest.status.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status as http
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import PICKUP_FLOW, PICKUP_STATUS_LABELS, PickupStatus
from app.models import (
    Credit,
    CreditTransaction,
    HouseholdReturn,
    Notification,
    PickupRequest,
    PickupStatusHistory,
    User,
)
from app.services import email as email_service


def notify(db: Session, user_id: int, title: str, body: str,
           category: str = "PICKUP") -> Notification:
    record = Notification(user_id=user_id, title=title, body=body, category=category)
    db.add(record)
    db.flush()
    return record


def _award_credits(db: Session, pickup: PickupRequest, user: User) -> None:
    """Create the credit transaction. Only ever called on CREDITS_AWARDED.

    Idempotent: a pickup can never be paid twice, even if an operator
    replays the transition or two requests race.
    """
    existing = db.execute(
        select(CreditTransaction).where(
            CreditTransaction.pickup_id == pickup.pickup_id,
            CreditTransaction.status == "AWARDED",
        )
    ).scalar_one_or_none()
    if existing is not None:
        return

    amount = settings.CREDITS_PER_VERIFIED_RETURN

    wallet = db.execute(
        select(Credit).where(Credit.user_id == user.id).with_for_update()
    ).scalar_one_or_none()
    if wallet is None:
        wallet = Credit(user_id=user.id, balance=0, lifetime_earned=0)
        db.add(wallet)
        db.flush()

    wallet.balance += amount
    wallet.lifetime_earned += amount
    wallet.updated_at = datetime.utcnow()

    db.add(CreditTransaction(
        user_id=user.id,
        pickup_id=pickup.pickup_id,
        amount=amount,
        reason="Verified medicine return",
        status="AWARDED",
    ))
    db.flush()

    notify(db, user.id, f"{amount} MedCredits awarded",
           f"Your return on {pickup.pickup_id} was verified.", category="CREDIT")
    email_service.credits_email(db, user, pickup.pickup_id, amount, wallet.balance)


def transition(db: Session, pickup: PickupRequest, new_status: PickupStatus,
               actor: Optional[User] = None, note: Optional[str] = None) -> PickupRequest:
    """Move a pickup one step along the lifecycle.

    Rules:
      - CANCELLED may be reached from any non-terminal state.
      - Otherwise the new status must be the immediate next step. Skipping
        stages would leave gaps in the audit trail and, worse, allow credits
        to be awarded without a recorded verification.
    """
    current = PickupStatus(pickup.status)

    if current in (PickupStatus.COMPLETED, PickupStatus.CANCELLED):
        raise HTTPException(http.HTTP_409_CONFLICT,
                            detail=f"Pickup {pickup.pickup_id} is already {current.value}.")

    if new_status is PickupStatus.CANCELLED:
        pass
    else:
        try:
            expected = PICKUP_FLOW[PICKUP_FLOW.index(current) + 1]
        except (ValueError, IndexError):
            raise HTTPException(http.HTTP_409_CONFLICT,
                                detail=f"No transition available from {current.value}.")
        if new_status is not expected:
            raise HTTPException(
                http.HTTP_409_CONFLICT,
                detail=(f"Cannot move {pickup.pickup_id} from {current.value} to "
                        f"{new_status.value}. Next step is {expected.value}."),
            )

    if new_status is PickupStatus.ASSIGNED and pickup.collector_id is None:
        raise HTTPException(http.HTTP_400_BAD_REQUEST,
                            detail="Assign a collector before this step.")

    now = datetime.utcnow()
    pickup.status = new_status.value
    if new_status is PickupStatus.ASSIGNED:
        pickup.assigned_at = now
    elif new_status is PickupStatus.COLLECTED:
        pickup.collected_at = now
    elif new_status is PickupStatus.VERIFIED:
        pickup.verified_at = now
        # Mark the linked return records as verified too.
        returns = db.execute(
            select(HouseholdReturn).where(HouseholdReturn.pickup_id == pickup.pickup_id)
        ).scalars().all()
        for item in returns:
            item.verified_at = now

    db.add(PickupStatusHistory(
        pickup_request_id=pickup.id,
        status=new_status.value,
        note=note,
        changed_by=actor.id if actor else None,
    ))

    owner = db.get(User, pickup.user_id)
    label = PICKUP_STATUS_LABELS.get(new_status, new_status.value)

    if new_status is PickupStatus.CREDITS_AWARDED:
        _award_credits(db, pickup, owner)
    else:
        notify(db, owner.id, label, f"Pickup {pickup.pickup_id}: {label.lower()}.")
        email_service.pickup_email(db, owner, pickup, new_status)

    db.flush()
    return pickup
