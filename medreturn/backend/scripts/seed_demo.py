"""Seed demo data for a presentation.

    python -m scripts.seed_demo

Creates hospitals, collectors, four logins, a spread of waste events
across the confidence gate, and pickups at different lifecycle stages so
every dashboard has something to show.

DO NOT run this against a production database. Every account here uses a
known password.
"""

import random
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.core.constants import (
    SUPPORTED_RETURN_CATEGORIES,
    SUPPORTED_WASTE_CLASSES,
    Decision,
    Eligibility,
    PickupStatus,
    QuarantineStatus,
    Role,
)
from app.core.security import hash_password
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.ml.decision import route_waste
from app.models import (
    Collector,
    Credit,
    Hospital,
    HouseholdReturn,
    ModelVersion,
    PickupRequest,
    QuarantineEvent,
    User,
    WasteEvent,
)
from app.services.ids import next_id
from app.services.pickups import transition

DEMO_PASSWORD = "medreturn123"
LOCATIONS = ["Ward 3 Inlet", "OT Block Inlet", "Lab Inlet", "ICU Inlet"]


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.execute(select(User).limit(1)).scalar_one_or_none():
            print("Database already has users. Drop the schema first to reseed.")
            return

        # --- hospitals ---
        hospitals = [
            Hospital(name="Civil Hospital Ludhiana", city="Ludhiana", beds=520,
                     contact_email="ops@civilhospital.in", status="ACTIVE"),
            Hospital(name="DMC & Hospital", city="Ludhiana", beds=1150,
                     contact_email="waste@dmch.in", status="ACTIVE"),
            Hospital(name="SPS Hospital", city="Ludhiana", beds=300,
                     contact_email="facility@sps.in", status="PENDING"),
        ]
        db.add_all(hospitals)
        db.flush()

        # --- users ---
        def make_user(username, name, email, role, **kwargs) -> User:
            user = User(
                username=username, full_name=name, email=email, role=role,
                password_hash=hash_password(DEMO_PASSWORD), **kwargs
            )
            db.add(user)
            db.flush()
            return user

        rhea = make_user(
            "rhea", "Rhea Sharma", "rhea@demo.in", Role.HOUSEHOLD.value,
            phone="+91 98150 44120",
            address="Flat 204, Silver Oak Residency, Model Town, Ludhiana 141002",
        )
        kabir = make_user(
            "kabir", "Kabir Malhotra", "kabir@demo.in", Role.HOUSEHOLD.value,
            phone="+91 97800 51234",
            address="H.No. 18, Sarabha Nagar, Ludhiana 141001",
        )
        make_user("operator", "Dr. Anil Verma", "ops@civilhospital.in",
                  Role.HOSPITAL.value, phone="+91 98765 11002",
                  hospital_id=hospitals[0].id)
        make_user("admin", "System Administrator", "admin@medreturn.in",
                  Role.ADMIN.value, phone="+91 98765 00000")
        collector_user = make_user(
            "collector", "Manpreet Singh", "manpreet@medreturn.in",
            Role.COLLECTOR.value, phone="+91 99887 32211",
        )

        db.add_all([
            Credit(user_id=rhea.id, balance=0, lifetime_earned=0),
            Credit(user_id=kabir.id, balance=0, lifetime_earned=0),
        ])

        # --- collectors ---
        collectors = [
            Collector(user_id=collector_user.id, name="Manpreet Singh",
                      phone="+91 99887 32211", vehicle_number="PB10 AB 4412",
                      zone="Zone 3 - Model Town", status="ON_DUTY"),
            Collector(name="Simran Kaur", phone="+91 99887 65432",
                      vehicle_number="PB10 CD 7781",
                      zone="Zone 1 - Sarabha Nagar", status="ON_DUTY"),
            Collector(name="Harjit Rai", phone="+91 98111 22334",
                      vehicle_number="PB10 EF 2290", zone="Zone 5 - Dugri",
                      status="OFF_DUTY"),
        ]
        db.add_all(collectors)
        db.flush()

        # --- model versions (metrics deliberately left NULL) ---
        db.add_all([
            ModelVersion(name="MobileNetV3-Small", version="v1.0",
                         dataset_version="ds-2025-09 (pilot, 1840 images)",
                         trained_at=datetime(2025, 11, 14), status="ARCHIVED",
                         notes="Pilot run. Not evaluated on a held-out split."),
            ModelVersion(name="MobileNetV3-Small", version="v1.1",
                         dataset_version="ds-2026-01 (4120 images)",
                         trained_at=datetime(2026, 2, 2), status="ARCHIVED",
                         notes="Metrics pending evaluation."),
            ModelVersion(name="MobileNetV3-Small", version="v1.2",
                         dataset_version="ds-2026-04 (6905 images)",
                         trained_at=datetime(2026, 5, 19), status="DEPLOYED",
                         notes="Run ml/evaluate.py to populate real metrics."),
        ])

        # --- waste events across the gate ---
        random.seed(20260918)
        for index in range(48):
            predicted = random.choice(SUPPORTED_WASTE_CLASSES)
            confidence = round(random.uniform(0.55, 0.99), 2)
            routing = route_waste(predicted, confidence, SUPPORTED_WASTE_CLASSES)
            created = datetime.utcnow() - timedelta(
                days=random.randint(0, 10), hours=random.randint(0, 20)
            )
            event = WasteEvent(
                event_id=next_id(db, "waste"),
                hospital_id=hospitals[1].id if index % 7 == 0 else hospitals[0].id,
                predicted_class=predicted,
                confidence=confidence,
                weight_kg=round(random.uniform(0.2, 3.6), 2),
                location=LOCATIONS[index % len(LOCATIONS)],
                decision=routing.decision,
                route=routing.route,
                reason=routing.reason,
                inference_mode="DEMO",
                model_version="v1.2-demo",
                created_at=created,
            )
            db.add(event)
            db.flush()
            if routing.decision == Decision.QUARANTINED.value:
                db.add(QuarantineEvent(
                    quarantine_id=next_id(db, "quarantine"),
                    waste_event_id=event.id,
                    reason=routing.reason,
                    status=QuarantineStatus.QUARANTINED.value,
                    created_at=created,
                ))

        db.commit()

        # --- pickups at different stages ---
        def make_pickup(user: User, days_ahead: int, slot: str, items: int,
                        weight: float, notes: str = "") -> PickupRequest:
            pickup = PickupRequest(
                pickup_id=next_id(db, "pickup"),
                user_id=user.id,
                address=user.address,
                contact_phone=user.phone,
                latitude=30.9010 + random.uniform(-0.02, 0.02),
                longitude=75.8573 + random.uniform(-0.02, 0.02),
                preferred_date=(date.today() + timedelta(days=days_ahead)).isoformat(),
                time_slot=slot,
                item_count=items,
                approx_weight_kg=weight,
                notes=notes,
                status=PickupStatus.REQUESTED.value,
            )
            db.add(pickup)
            db.flush()
            return pickup

        def advance(pickup: PickupRequest, target: PickupStatus,
                    collector_id: int | None = None) -> None:
            from app.core.constants import PICKUP_FLOW

            if collector_id:
                pickup.collector_id = collector_id
            index = PICKUP_FLOW.index(PickupStatus(pickup.status))
            stop = PICKUP_FLOW.index(target)
            while index < stop:
                index += 1
                transition(db, pickup, PICKUP_FLOW[index])

        finished = make_pickup(rhea, 0, "10:00-13:00", 3, 0.4,
                               "Two expired strips and a cough syrup bottle.")
        advance(finished, PickupStatus.COMPLETED, collectors[0].id)

        en_route = make_pickup(rhea, 1, "14:00-17:00", 2, 0.25,
                               "Leftover antibiotics after the course finished.")
        advance(en_route, PickupStatus.ON_THE_WAY, collectors[0].id)

        scheduled = make_pickup(kabir, 2, "09:00-12:00", 5, 0.8)
        advance(scheduled, PickupStatus.SCHEDULED)

        make_pickup(kabir, 3, "17:00-20:00", 1, 0.1, "Expired inhaler.")

        # --- household return records ---
        db.add_all([
            HouseholdReturn(
                user_id=rhea.id, detected_item="Tablet Strip",
                category="Tablet Strip", confidence=0.91,
                eligibility_status=Eligibility.ELIGIBLE.value,
                inference_mode="DEMO", pickup_id=finished.pickup_id,
                verified_at=datetime.utcnow(),
            ),
            HouseholdReturn(
                user_id=rhea.id, detected_item="Syrup Bottle",
                category="Syrup Bottle", confidence=0.84,
                eligibility_status=Eligibility.ELIGIBLE.value,
                inference_mode="DEMO", pickup_id=finished.pickup_id,
                verified_at=datetime.utcnow(),
            ),
            HouseholdReturn(
                user_id=rhea.id, detected_item="Capsule Blister",
                category="Capsule Blister", confidence=0.88,
                eligibility_status=Eligibility.ELIGIBLE.value,
                inference_mode="DEMO", pickup_id=en_route.pickup_id,
            ),
            HouseholdReturn(
                user_id=kabir.id, detected_item="Ointment Tube",
                category="Unknown", confidence=0.41,
                eligibility_status=Eligibility.NEEDS_REVIEW.value,
                inference_mode="DEMO",
            ),
        ])

        db.commit()

        print("Seed complete.\n")
        print(f"  Password for every demo account: {DEMO_PASSWORD}\n")
        for username, role in [("rhea", "household"), ("operator", "hospital"),
                               ("admin", "admin"), ("collector", "collector")]:
            print(f"  {username:<12} {role}")
        print(f"\n  Supported return categories: {', '.join(SUPPORTED_RETURN_CATEGORIES)}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
