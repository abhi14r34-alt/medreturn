"""Create all tables. Run once, or use Alembic for real migrations."""

import logging

from app.db.session import Base, engine
from app.models import entities  # noqa: F401  (registers the mappers)

logger = logging.getLogger(__name__)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created (existing tables are left untouched).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("Schema ready.")
