"""The confidence gate.

One place decides whether an item is routed or held. Both the hospital
line and the household analyzer call it, so the rule cannot drift apart
between the two workflows.
"""

from dataclasses import dataclass
from typing import List, Optional

from app.core.config import settings
from app.core.constants import Decision, Eligibility


@dataclass
class Routing:
    decision: str
    route: str
    reason: Optional[str]


def route_waste(predicted_class: str, confidence: float,
                supported: List[str],
                threshold: Optional[float] = None) -> Routing:
    """Accept only when the class is supported AND confidence clears the bar.

    Anything else is quarantined for human verification. Low-confidence
    items are never routed automatically, whatever the predicted class.
    """
    threshold = settings.CONFIDENCE_THRESHOLD if threshold is None else threshold

    if predicted_class not in supported:
        return Routing(
            decision=Decision.QUARANTINED.value,
            route="QUARANTINE BAY",
            reason="Predicted class is outside the configured supported list",
        )

    if confidence < threshold:
        return Routing(
            decision=Decision.QUARANTINED.value,
            route="QUARANTINE BAY",
            reason=f"Confidence {confidence:.2f} is below threshold {threshold:.2f}",
        )

    compartment = chr(ord("A") + supported.index(predicted_class))
    return Routing(
        decision=Decision.ACCEPTED.value,
        route=f"COMPARTMENT {compartment}",
        reason=None,
    )


def eligibility_for_return(predicted_class: str, confidence: float,
                           supported: List[str],
                           threshold: Optional[float] = None) -> str:
    """Household equivalent of the gate.

    Note what this does not do: it says nothing about whether a medicine is
    safe, genuine or legal. It only reports whether the packaging looks like
    a category the return programme accepts.
    """
    threshold = settings.CONFIDENCE_THRESHOLD if threshold is None else threshold

    if predicted_class not in supported:
        return Eligibility.UNSUPPORTED.value
    if confidence < threshold:
        return Eligibility.NEEDS_REVIEW.value
    return Eligibility.ELIGIBLE.value
