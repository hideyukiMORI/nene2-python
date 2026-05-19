"""Database utility helpers."""

from datetime import UTC, datetime


def parse_db_datetime(value: str | datetime) -> datetime:
    """Parse a DATETIME column value from SQLAlchemy into a UTC-aware datetime.

    Handles the two common cases:
    - SQLite: returns DATETIME columns as strings ("2026-05-20 12:34:56")
    - MySQL / PostgreSQL: may return datetime objects (naive or aware)

    All values are normalised to UTC-aware datetimes.

    Usage in a row-to-entity helper::

        from nene2.database import parse_db_datetime

        def _to_post(row: dict[str, Any]) -> Post:
            return Post(
                id=row["id"],
                title=row["title"],
                created_at=parse_db_datetime(row["created_at"]),
            )
    """
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(value).replace(tzinfo=UTC)
