"""ORM models.

Table list matches the SIH26115 specification: users, hospitals,
waste_events, quarantine_events, household_returns, pickup_requests,
pickup_status_history, collectors, credits, credit_transactions,
notifications, email_logs, model_versions.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import (
    Decision,
    Eligibility,
    PickupStatus,
    QuarantineStatus,
    Role,
)
from app.db.session import Base


def _now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(190), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=Role.HOUSEHOLD.value, nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    hospital_id: Mapped[int | None] = mapped_column(ForeignKey("hospitals.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    hospital = relationship("Hospital", back_populates="staff")
    pickups = relationship("PickupRequest", back_populates="user",
                           foreign_keys="PickupRequest.user_id")
    credit = relationship("Credit", back_populates="user", uselist=False)


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(190), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(String(190))
    beds: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    staff = relationship("User", back_populates="hospital")
    waste_events = relationship("WasteEvent", back_populates="hospital")


class WasteEvent(Base):
    """One item through the hospital segregation line."""

    __tablename__ = "waste_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    hospital_id: Mapped[int] = mapped_column(
        ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    predicted_class: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    location: Mapped[str | None] = mapped_column(String(120))
    image_path: Mapped[str | None] = mapped_column(String(255))
    item_name: Mapped[str | None] = mapped_column(String(190))
    expiry_date: Mapped[str | None] = mapped_column(String(32))
    batch_number: Mapped[str | None] = mapped_column(String(64))

    decision: Mapped[str] = mapped_column(String(20), default=Decision.QUARANTINED.value)
    route: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(String(255))

    model_version: Mapped[str | None] = mapped_column(String(32))
    inference_mode: Mapped[str] = mapped_column(String(16), default="DEMO")

    verification_status: Mapped[str | None] = mapped_column(String(32))
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)

    hospital = relationship("Hospital", back_populates="waste_events")
    quarantine = relationship("QuarantineEvent", back_populates="event", uselist=False)


class QuarantineEvent(Base):
    __tablename__ = "quarantine_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quarantine_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    waste_event_id: Mapped[int] = mapped_column(
        ForeignKey("waste_events.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default=QuarantineStatus.QUARANTINED.value)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewer_note: Mapped[str | None] = mapped_column(Text)
    corrected_class: Mapped[str | None] = mapped_column(String(64))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    event = relationship("WasteEvent", back_populates="quarantine")


class HouseholdReturn(Base):
    __tablename__ = "household_returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_path: Mapped[str | None] = mapped_column(String(255))
    item_name: Mapped[str | None] = mapped_column(String(190))
    expiry_date: Mapped[str | None] = mapped_column(String(32))
    batch_number: Mapped[str | None] = mapped_column(String(64))
    detected_item: Mapped[str | None] = mapped_column(String(190))
    category: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float | None] = mapped_column(Float)
    eligibility_status: Mapped[str] = mapped_column(
        String(24), default=Eligibility.NEEDS_REVIEW.value
    )
    inference_mode: Mapped[str] = mapped_column(String(16), default="DEMO")
    pickup_id: Mapped[str | None] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)


class Collector(Base):
    __tablename__ = "collectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    vehicle_number: Mapped[str | None] = mapped_column(String(32))
    zone: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="ON_DUTY")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class PickupRequest(Base):
    __tablename__ = "pickup_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pickup_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collector_id: Mapped[int | None] = mapped_column(
        ForeignKey("collectors.id", ondelete="SET NULL")
    )

    address: Mapped[str] = mapped_column(Text, nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    preferred_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    time_slot: Mapped[str] = mapped_column(String(32), nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, default=1)
    approx_weight_kg: Mapped[float] = mapped_column(Float, default=0.1)
    notes: Mapped[str | None] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String(255))
    proof_image_path: Mapped[str | None] = mapped_column(String(255))

    status: Mapped[str] = mapped_column(
        String(24), default=PickupStatus.REQUESTED.value, index=True
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)

    user = relationship("User", back_populates="pickups", foreign_keys=[user_id])
    collector = relationship("Collector")
    history = relationship(
        "PickupStatusHistory", back_populates="pickup",
        cascade="all, delete-orphan", order_by="PickupStatusHistory.created_at",
    )


class PickupStatusHistory(Base):
    __tablename__ = "pickup_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pickup_request_id: Mapped[int] = mapped_column(
        ForeignKey("pickup_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    pickup = relationship("PickupRequest", back_populates="history")


class Credit(Base):
    __tablename__ = "credits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    balance: Mapped[int] = mapped_column(Integer, default=0)
    lifetime_earned: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    user = relationship("User", back_populates="credit")


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pickup_id: Mapped[str | None] = mapped_column(String(32), index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(190), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="AWARDED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(190), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32), default="PICKUP")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    recipient: Mapped[str] = mapped_column(String(190), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    pickup_id: Mapped[str | None] = mapped_column(String(32))
    transport: Mapped[str] = mapped_column(String(32), default="console")
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_version: Mapped[str | None] = mapped_column(String(120))
    trained_at: Mapped[datetime | None] = mapped_column(DateTime)
    # Metrics stay NULL until ml/evaluate.py writes real numbers from a
    # held-out test split. They are never populated with placeholders.
    accuracy: Mapped[float | None] = mapped_column(Float)
    precision: Mapped[float | None] = mapped_column(Float)
    recall: Mapped[float | None] = mapped_column(Float)
    f1_score: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="ARCHIVED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Sequence(Base):
    """Counter table backing human-readable IDs (MR-PU-2026-000123)."""

    __tablename__ = "sequences"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)
