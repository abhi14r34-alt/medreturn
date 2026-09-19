"""Pydantic v2 schemas.

Response models exist partly for documentation and partly for privacy: the
household address, for example, only appears on schemas served to the
owner, an admin, or the assigned collector.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import PickupStatus


# --------------------------------------------------------------- auth
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[str] = Field(default=None, max_length=32)
    address: str = Field(min_length=10, max_length=500)

    @field_validator("username")
    @classmethod
    def _clean_username(cls, v: str) -> str:
        v = v.strip().lower()
        if not v.replace("_", "").replace(".", "").isalnum():
            raise ValueError(
                "Username may contain letters, numbers, dots and underscores only."
            )
        return v


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str
    hospital_id: Optional[int] = None
    created_at: datetime


class UserWithAddressOut(UserOut):
    address: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserWithAddressOut


class ProfileUpdateIn(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    phone: Optional[str] = Field(default=None, max_length=32)
    address: Optional[str] = Field(default=None, min_length=10, max_length=500)


# ---------------------------------------------------- household returns
class AnalysisOut(BaseModel):
    """Result of one household image analysis."""

    return_id: int
    detected_item: Optional[str]
    item_name: Optional[str] = None
    expiry_date: Optional[str] = None
    batch_number: Optional[str] = None
    category: Optional[str]
    confidence: float
    confidence_threshold: float
    eligibility_status: str
    inference_mode: str = Field(description="REAL or DEMO")
    is_simulated: bool
    model_version: str
    ocr_text: Optional[str] = None
    ocr_available: bool = False
    human_verification_required: bool = False
    model_quality: dict = Field(default_factory=dict)
    message: str
    supported_categories: List[str]
    disclaimer: str = (
        "This analysis assists with packaging identification only. It cannot "
        "determine whether a medicine is safe, genuine or legal from an image."
    )


class HouseholdReturnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    detected_item: Optional[str]
    category: Optional[str]
    confidence: Optional[float]
    eligibility_status: str
    inference_mode: str
    pickup_id: Optional[str]
    created_at: datetime
    verified_at: Optional[datetime]


# ------------------------------------------------------------- pickups
class PickupCreateIn(BaseModel):
    address: str = Field(min_length=10, max_length=500)
    contact_phone: str = Field(min_length=6, max_length=32)
    preferred_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    time_slot: str = Field(min_length=3, max_length=32)
    item_count: int = Field(ge=1, le=99)
    approx_weight_kg: float = Field(gt=0, le=50)
    notes: Optional[str] = Field(default=None, max_length=1000)
    return_id: Optional[int] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    @field_validator("preferred_date")
    @classmethod
    def _not_in_the_past(cls, v: str) -> str:
        from datetime import date

        if date.fromisoformat(v) < date.today():
            raise ValueError("Preferred date cannot be in the past.")
        return v


class StatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    note: Optional[str]
    created_at: datetime


class CollectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: Optional[str]
    vehicle_number: Optional[str]
    zone: Optional[str]
    status: str


class PickupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pickup_id: str
    status: str
    preferred_date: str
    time_slot: str
    item_count: int
    approx_weight_kg: float
    notes: Optional[str]
    created_at: datetime
    assigned_at: Optional[datetime]
    collected_at: Optional[datetime]
    verified_at: Optional[datetime]
    collector: Optional[CollectorOut] = None


class PickupDetailOut(PickupOut):
    """Includes the address. Served only to the owner, admins and the
    assigned collector."""

    address: str
    contact_phone: Optional[str]
    history: List[StatusHistoryOut] = []


class TrackingOut(BaseModel):
    pickup_id: str
    status: str
    demo: bool
    collector_lat: Optional[float]
    collector_lng: Optional[float]
    destination_lat: Optional[float]
    destination_lng: Optional[float]
    eta_minutes: Optional[int]
    distance_km: Optional[float]
    note: str


class StatusUpdateIn(BaseModel):
    status: PickupStatus
    note: Optional[str] = Field(default=None, max_length=255)


class AssignCollectorIn(BaseModel):
    collector_id: int


# ------------------------------------------------------------- credits
class CreditsOut(BaseModel):
    balance: int
    lifetime_earned: int
    pending: int
    credits_per_verified_return: int


class CreditTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pickup_id: Optional[str]
    amount: int
    reason: str
    status: str
    created_at: datetime


# ------------------------------------------------------- notifications
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: Optional[str]
    category: str
    is_read: bool
    created_at: datetime


# ------------------------------------------------------ hospital waste
class WastePredictionOut(BaseModel):
    event_id: str
    predicted_class: str
    item_name: Optional[str] = None
    expiry_date: Optional[str] = None
    batch_number: Optional[str] = None
    confidence: float
    confidence_threshold: float
    decision: str
    route: str
    reason: Optional[str]
    weight_kg: Optional[float]
    location: Optional[str]
    inference_mode: str
    is_simulated: bool
    model_version: str
    hardware_simulated: bool
    hardware_detail: str
    ocr_text: Optional[str] = None
    ocr_available: bool = False
    human_verification_required: bool = False
    model_quality: dict = Field(default_factory=dict)
    supported_classes: List[str]


class WasteEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    predicted_class: str
    item_name: Optional[str] = None
    expiry_date: Optional[str] = None
    batch_number: Optional[str] = None
    confidence: float
    weight_kg: Optional[float]
    location: Optional[str]
    decision: str
    route: Optional[str]
    reason: Optional[str]
    inference_mode: str
    model_version: Optional[str]
    verification_status: Optional[str]
    verified_at: Optional[datetime]
    created_at: datetime


class QuarantineOut(BaseModel):
    quarantine_id: str
    status: str
    reason: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]
    reviewer_note: Optional[str]
    corrected_class: Optional[str]
    event: WasteEventOut


class QuarantineVerifyIn(BaseModel):
    release: bool = Field(
        description="True verifies and releases; False keeps the item held."
    )
    corrected_class: Optional[str] = Field(default=None, max_length=64)
    note: Optional[str] = Field(default=None, max_length=1000)


# --------------------------------------------------------------- admin
class HospitalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    city: Optional[str]
    beds: Optional[int]
    contact_email: Optional[str]
    status: str


class ModelVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    version: str
    dataset_version: Optional[str]
    trained_at: Optional[datetime]
    accuracy: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    status: str
    notes: Optional[str]


class ModelInfoOut(BaseModel):
    runtime: dict
    versions: List[ModelVersionOut]
    metrics_note: str = (
        "Metrics stay null until ml/evaluate.py writes real figures from a "
        "held-out test split. Placeholder numbers are never shown."
    )


class AdminDashboardOut(BaseModel):
    household_returns: int
    waste_events: int
    quarantined_open: int
    pickups_total: int
    pickups_completed: int
    completion_rate: float
    credits_distributed: int
    average_confidence: Optional[float]
    category_distribution: dict
    pickups_by_status: dict


class SettingsOut(BaseModel):
    demo_mode: bool
    confidence_threshold: float
    credits_per_verified_return: int
    supported_waste_classes: List[str]
    supported_return_categories: List[str]
    email_transport: str
    maps_provider: str
    hardware_simulated: bool
