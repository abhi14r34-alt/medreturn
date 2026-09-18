"""Domain constants shared by the decision engine, the API and the seeds."""

from enum import Enum


class Role(str, Enum):
    HOUSEHOLD = "household"
    HOSPITAL = "hospital"
    ADMIN = "admin"
    COLLECTOR = "collector"


class PickupStatus(str, Enum):
    REQUESTED = "REQUESTED"
    SCHEDULED = "SCHEDULED"
    ASSIGNED = "ASSIGNED"
    ON_THE_WAY = "ON_THE_WAY"
    ARRIVED = "ARRIVED"
    COLLECTED = "COLLECTED"
    VERIFIED = "VERIFIED"
    CREDITS_AWARDED = "CREDITS_AWARDED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# The lifecycle in order. Transitions may only move forward one step at a
# time (or jump to CANCELLED), which keeps the audit trail coherent.
PICKUP_FLOW = [
    PickupStatus.REQUESTED,
    PickupStatus.SCHEDULED,
    PickupStatus.ASSIGNED,
    PickupStatus.ON_THE_WAY,
    PickupStatus.ARRIVED,
    PickupStatus.COLLECTED,
    PickupStatus.VERIFIED,
    PickupStatus.CREDITS_AWARDED,
    PickupStatus.COMPLETED,
]

PICKUP_STATUS_LABELS = {
    PickupStatus.REQUESTED: "Pickup requested",
    PickupStatus.SCHEDULED: "Pickup scheduled",
    PickupStatus.ASSIGNED: "Collector assigned",
    PickupStatus.ON_THE_WAY: "Pickup on the way",
    PickupStatus.ARRIVED: "Collector arrived",
    PickupStatus.COLLECTED: "Items collected",
    PickupStatus.VERIFIED: "Items verified",
    PickupStatus.CREDITS_AWARDED: "Credits awarded",
    PickupStatus.COMPLETED: "Completed",
    PickupStatus.CANCELLED: "Pickup cancelled",
}


class Decision(str, Enum):
    ACCEPTED = "ACCEPTED"
    QUARANTINED = "QUARANTINED"


class QuarantineStatus(str, Enum):
    QUARANTINED = "QUARANTINED"
    VERIFIED_RELEASED = "VERIFIED_RELEASED"
    KEPT = "KEPT"


class Eligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNSUPPORTED = "UNSUPPORTED"


# IMPORTANT: these lists must match the labels the model was actually
# trained on. Editing them here without retraining will produce wrong
# routing. ml/config.py is the single source of truth at training time.
SUPPORTED_WASTE_CLASSES = [
    "Sharps",
    "Infectious",
    "Pharmaceutical",
    "Glass",
    "Plastic Recyclable",
    "General",
]

SUPPORTED_RETURN_CATEGORIES = [
    "Tablet Strip",
    "Syrup Bottle",
    "Capsule Blister",
    "Ointment Tube",
    "Inhaler",
    "Injection Vial",
]

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
