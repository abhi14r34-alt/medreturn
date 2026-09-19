"""Email notification service.

Transport is chosen from configuration:
  - EMAIL_ENABLED=true and SMTP_HOST set -> real SMTP delivery
  - otherwise                         -> console transport (logged, not sent)

Swapping in SendGrid or SES means adding one _send_* function and one
branch in send_email(). Callers never change. Credentials come only from
the environment.

Every attempt is written to email_logs whether or not delivery succeeded,
so the admin dashboard can show what went out and what failed.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
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
    if settings.SMTP_REPLY_TO:
        message["Reply-To"] = settings.SMTP_REPLY_TO
    message.set_content(body)

    tls_context = ssl.create_default_context()
    if settings.SMTP_SSL:
        server_client = smtplib.SMTP_SSL(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=settings.SMTP_TIMEOUT_SECONDS,
            context=tls_context,
        )
    else:
        server_client = smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=settings.SMTP_TIMEOUT_SECONDS,
        )

    with server_client as server:
        if settings.SMTP_TLS and not settings.SMTP_SSL:
            server.ehlo()
            server.starttls(context=tls_context)
            server.ehlo()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)


def send_email(db: Session, user: Optional[User], subject: str, body: str,
               pickup_id: Optional[str] = None) -> EmailLog:
    """Send (or log) one message and record the attempt."""
    recipient = user.email if user else settings.SMTP_FROM
    transport = settings.email_transport
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
        logger.info("[%s email] to=%s subject=%s", transport, recipient, subject)

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


def analysis_email(
    db: Session,
    user: User,
    *,
    detected_item: str | None,
    model_label: str | None,
    confidence: float | None,
    review_required: bool,
) -> EmailLog | None:
    """Optionally notify a user of a completed image analysis.

    This is opt-in because an upload can be retried several times. It uses the
    model label exactly as returned by the checkpoint; no email template maps
    it back to a fixed category list.
    """
    if not settings.EMAIL_SEND_ANALYSIS_RESULTS:
        return None

    subject = "MedReturn analysis complete"
    confidence_text = f"{confidence * 100:.0f}%" if confidence is not None else "unavailable"
    review_text = (
        "A team member will review this item before it is accepted."
        if review_required
        else "The image passed the configured review checks."
    )
    body = "\n".join([
        f"Hello {user.full_name},",
        "",
        "Your medicine-return image was analysed.",
        f"Item:       {detected_item or 'Not identified'}",
        f"Model label: {model_label or 'Not identified'}",
        f"Confidence: {confidence_text}",
        "",
        review_text,
        "",
        SUPPORT_LINE,
    ])
    return send_email(db, user, subject, body)
