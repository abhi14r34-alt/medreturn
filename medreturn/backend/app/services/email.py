"""Email notification service.

Transport is chosen from configuration:
  - SMTP_HOST set   -> real SMTP delivery
  - SMTP_HOST blank -> console transport (logged and recorded, not sent)

Swapping in SendGrid or SES means adding one _send_* function and one
branch in send_email(). Callers never change. Credentials come only from
the environment.

Every attempt is written to email_logs whether or not delivery succeeded,
so the admin dashboard can show what went out and what failed.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import PICKUP_STATUS_LABELS, PickupStatus
from app.models import EmailLog, PickupRequest, User

logger = logging.getLogger(__name__)

SUPPORT_LINE = "Support: support@medreturn.in | 1800-123-4567"


def _send_smtp(to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
        if settings.SMTP_TLS:
            server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)


def send_email(db: Session, user: Optional[User], subject: str, body: str,
               pickup_id: Optional[str] = None) -> EmailLog:
    """Send (or log) one message and record the attempt."""
    recipient = user.email if user else settings.SMTP_FROM
    transport = "smtp" if settings.email_configured else "console"
    delivered = False
    error: Optional[str] = None

    if settings.email_configured:
        try:
            _send_smtp(recipient, subject, body)
            delivered = True
        except Exception as exc:  # noqa: BLE001 - a failed email must not
            error = f"{type(exc).__name__}: {exc}"[:255]  # break the workflow
            logger.error("Email to %s failed: %s", recipient, error)
    else:
        logger.info("[console email] to=%s subject=%s", recipient, subject)

    record = EmailLog(
        user_id=user.id if user else None,
        recipient=recipient,
        subject=subject,
        body=body,
        pickup_id=pickup_id,
        transport=transport,
        delivered=delivered,
        error=error,
    )
    db.add(record)
    db.flush()
    return record


def pickup_email(db: Session, user: User, pickup: PickupRequest,
                 status: PickupStatus) -> EmailLog:
    """Templated status email for a pickup."""
    label = PICKUP_STATUS_LABELS.get(status, status.value)
    subject = f"MedReturn {label} - {pickup.pickup_id}"
    body = "\n".join([
        f"Hello {user.full_name},",
        "",
        f"Your medicine return pickup is now: {label}.",
        "",
        f"Pickup ID:      {pickup.pickup_id}",
        f"Date:           {pickup.preferred_date}",
        f"Time slot:      {pickup.time_slot}",
        f"Address:        {pickup.address}",
        f"Items:          {pickup.item_count} (approx {pickup.approx_weight_kg} kg)",
        f"Current status: {label}",
        "",
        SUPPORT_LINE,
    ])
    return send_email(db, user, subject, body, pickup_id=pickup.pickup_id)


def credits_email(db: Session, user: User, pickup_id: str, amount: int,
                  balance: int) -> EmailLog:
    subject = f"MedReturn Credits Awarded - {pickup_id}"
    body = "\n".join([
        f"Hello {user.full_name},",
        "",
        f"Your return on {pickup_id} was verified and {amount} MedCredits "
        "have been added to your account.",
        "",
        f"New balance: {balance} MedCredits",
        "",
        SUPPORT_LINE,
    ])
    return send_email(db, user, subject, body, pickup_id=pickup_id)
