"""Human-readable identifiers backed by a counter table.

Format: MR-PU-2026-000123 / MR-WE-2026-000045 / MR-QE-2026-00012
The row is locked FOR UPDATE so two concurrent requests cannot take the
same number.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Sequence

PREFIXES = {"pickup": "MR-PU", "waste": "MR-WE", "quarantine": "MR-QE"}


def next_id(db: Session, kind: str) -> str:
    prefix = PREFIXES[kind]
    row = db.execute(
        select(Sequence).where(Sequence.name == kind).with_for_update()
    ).scalar_one_or_none()

    if row is None:
        row = Sequence(name=kind, value=0)
        db.add(row)
        db.flush()

    row.value += 1
    db.flush()
    return f"{prefix}-{datetime.utcnow().year}-{row.value:06d}"
