"""SQLAlchemy Core implementation of database interfaces.

Supports SQLite, MySQL, and PostgreSQL via SQLAlchemy's engine URL.
"""

from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

from .exceptions import DatabaseConnectionException
from .interfaces import DatabaseQueryExecutorInterface, DatabaseTransactionManagerInterface


class SqlAlchemyQueryExecutor(DatabaseQueryExecutorInterface):
    """Execute queries using SQLAlchemy Core (connection-per-call, no ORM)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def fetch_all(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                return [dict(row._mapping) for row in result]
        except OperationalError as exc:
            raise DatabaseConnectionException(str(exc)) from exc

    def fetch_one(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                row = result.fetchone()
                return dict(row._mapping) if row else None
        except OperationalError as exc:
            raise DatabaseConnectionException(str(exc)) from exc

    def write(self, sql: str, params: dict[str, Any] | None = None) -> int:
        try:
            with self._engine.begin() as conn:
                result = conn.execute(text(sql), params or {})
                return result.lastrowid or result.rowcount
        except OperationalError as exc:
            raise DatabaseConnectionException(str(exc)) from exc


class SqlAlchemyTransactionManager(DatabaseTransactionManagerInterface):
    """Manage an explicit transaction on a single SQLAlchemy connection."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._conn = engine.connect()
        self._tx: Any = None

    def begin(self) -> None:
        self._tx = self._conn.begin()

    def commit(self) -> None:
        if self._tx is not None:
            self._tx.commit()
            self._tx = None

    def rollback(self) -> None:
        if self._tx is not None:
            self._tx.rollback()
            self._tx = None
