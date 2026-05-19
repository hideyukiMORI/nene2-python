"""Schema bootstrap — ensures tables exist for in-memory SQLite or fresh deployments.

Production: use `alembic upgrade head` before starting the app.
In-memory SQLite (test/dev): tables are created here with IF NOT EXISTS.
"""

from sqlalchemy import Engine, text


def ensure_schema(engine: Engine) -> None:
    """Create tables if they do not already exist (idempotent)."""
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS notes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "title TEXT NOT NULL,"
            "body TEXT NOT NULL,"
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS tags ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "name TEXT NOT NULL UNIQUE,"
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS comments ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "note_id INTEGER NOT NULL,"
            "body TEXT NOT NULL,"
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
        ))
