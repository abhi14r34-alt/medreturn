"""Create all tables. Run once, or use Alembic for real migrations."""

import logging

from app.db.session import Base, engine
from app.models import entities  # noqa: F401  (registers the mappers)

logger = logging.getLogger(__name__)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    # Ensure new columns exist on existing databases
    with engine.connect() as conn:
        for table, col, col_type in [
            ("household_returns", "item_name", "VARCHAR(190)"),
            ("household_returns", "expiry_date", "VARCHAR(32)"),
            ("household_returns", "batch_number", "VARCHAR(64)"),
            ("waste_events", "item_name", "VARCHAR(190)"),
            ("waste_events", "expiry_date", "VARCHAR(32)"),
            ("waste_events", "batch_number", "VARCHAR(64)"),
        ]:
            try:
                from sqlalchemy import text
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
            except Exception:
                pass
    logger.info("Tables created and migration columns checked.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("Schema ready.")
