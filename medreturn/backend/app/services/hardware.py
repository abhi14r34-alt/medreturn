"""Smart-bin controller abstraction.

Prototype ships a simulated controller. The real one would POST the
routing command to a C/C++ firmware bridge which drives the servo gate.

    FastAPI -> HardwareController -> HTTP/serial bridge -> servo gate

Nothing in this module claims a physical device is connected. The API
returns `simulated: true` so the UI can label it honestly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RouteCommand:
    event_id: str
    compartment: str
    simulated: bool
    acknowledged: bool
    detail: str


class HardwareController:
    """Base interface. Implement send() for a real bridge."""

    simulated = True

    def send(self, event_id: str, compartment: str) -> RouteCommand:
        raise NotImplementedError


class SimulatedController(HardwareController):
    simulated = True

    def send(self, event_id: str, compartment: str) -> RouteCommand:
        logger.info("[hardware simulation] %s -> %s", event_id, compartment)
        return RouteCommand(
            event_id=event_id,
            compartment=compartment,
            simulated=True,
            acknowledged=True,
            detail="Hardware simulation: no physical gate is connected.",
        )


class HttpBridgeController(HardwareController):
    """Talks to a controller exposing POST {endpoint}/route."""

    simulated = False

    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")

    def send(self, event_id: str, compartment: str) -> RouteCommand:
        import urllib.error
        import urllib.request
        import json

        payload = json.dumps({"event_id": event_id, "compartment": compartment})
        request = urllib.request.Request(
            f"{self.endpoint}/route",
            data=payload.encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                ok = 200 <= response.status < 300
            return RouteCommand(event_id, compartment, False, ok,
                                "Controller acknowledged." if ok else "Controller refused.")
        except (urllib.error.URLError, TimeoutError) as exc:
            logger.error("Hardware bridge unreachable: %s", exc)
            return RouteCommand(event_id, compartment, False, False,
                                f"Controller unreachable: {exc}")


def get_controller() -> HardwareController:
    if settings.HARDWARE_ENDPOINT:
        return HttpBridgeController(settings.HARDWARE_ENDPOINT)
    return SimulatedController()
