"""Schema bootstrap — ensures tables exist for in-memory SQLite or fresh deployments.

Production: use `alembic upgrade head` before starting the app.
In-memory SQLite (test/dev): tables are created here with IF NOT EXISTS.
"""

import sqlite3

from sqlalchemy import Engine, event, text
from sqlalchemy.engine import Connection


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_conn: object, _connection_record: object) -> None:
    """Enable foreign-key enforcement for every new SQLite connection."""
    if isinstance(dbapi_conn, sqlite3.Connection):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


def ensure_schema(engine: Engine) -> None:
    """Create tables if they do not already exist (idempotent)."""
    with engine.begin() as conn:
        _create_tables(conn)


def _create_tables(conn: Connection) -> None:
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS notes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "title TEXT NOT NULL,"
            "body TEXT NOT NULL,"
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
    )
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS tags ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "name TEXT NOT NULL UNIQUE,"
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
    )
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS comments ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,"
            "body TEXT NOT NULL,"
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
    )
