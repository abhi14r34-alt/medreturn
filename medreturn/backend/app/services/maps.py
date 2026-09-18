"""Map/geolocation abstraction.

MAPS_PROVIDER=demo returns an interpolated position along a straight line
between the depot and the pickup address, flagged demo=True. Swap in a real
provider by implementing a MapsProvider and returning it from get_provider().

No live GPS is claimed anywhere. The frontend renders "Demo tracking" when
demo is true.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.config import settings
from app.core.constants import PickupStatus

# Depot the demo collector starts from (Ludhiana).
DEPOT_LAT, DEPOT_LNG = 30.8810, 75.8200

# How far along the route each stage is assumed to be.
STAGE_PROGRESS = {
    PickupStatus.ASSIGNED.value: 0.10,
    PickupStatus.ON_THE_WAY.value: 0.62,
    PickupStatus.ARRIVED.value: 1.0,
}


@dataclass
class TrackingSnapshot:
    demo: bool
    collector_lat: Optional[float]
    collector_lng: Optional[float]
    destination_lat: Optional[float]
    destination_lng: Optional[float]
    eta_minutes: Optional[int]
    distance_km: Optional[float]
    note: str


class MapsProvider:
    def track(self, pickup) -> TrackingSnapshot:
        raise NotImplementedError


class DemoMapsProvider(MapsProvider):
    def track(self, pickup) -> TrackingSnapshot:
        progress = STAGE_PROGRESS.get(pickup.status)
        dest_lat = pickup.latitude
        dest_lng = pickup.longitude

        if progress is None or dest_lat is None:
            return TrackingSnapshot(
                demo=True, collector_lat=None, collector_lng=None,
                destination_lat=dest_lat, destination_lng=dest_lng,
                eta_minutes=None, distance_km=None,
                note="Demo tracking: no vehicle is moving at this stage.",
            )

        lat = DEPOT_LAT + (dest_lat - DEPOT_LAT) * progress
        lng = DEPOT_LNG + (dest_lng - DEPOT_LNG) * progress
        remaining = round((1 - progress) * 8.5, 2)

        return TrackingSnapshot(
            demo=True,
            collector_lat=round(lat, 6),
            collector_lng=round(lng, 6),
            destination_lat=dest_lat,
            destination_lng=dest_lng,
            eta_minutes=max(1, int(remaining * 3)),
            distance_km=remaining,
            note="Demo tracking: simulated position, not a live GPS feed.",
        )


def get_provider() -> MapsProvider:
    # Add real providers here, e.g. if settings.MAPS_PROVIDER == "google": ...
    return DemoMapsProvider()
