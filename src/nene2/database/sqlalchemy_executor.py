"""SQLAlchemy Core implementation of database interfaces.

Supports SQLite, MySQL, and PostgreSQL via SQLAlchemy's engine URL.
"""

from collections.abc import Callable
from typing import Any

from sqlalchemy import Connection, CursorResult, Engine, text
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

from .exceptions import DatabaseConnectionException, DatabaseIntegrityException
from .interfaces import DatabaseQueryExecutorInterface, DatabaseTransactionManagerInterface


def _insert_id(conn: Connection, result: CursorResult[Any]) -> int:
    """Return the new row's PK after an INSERT, portably across dialects.

    SQLite and MySQL expose the value via DBAPI ``lastrowid``. PostgreSQL
    (psycopg2) does not, so fall back to ``lastval()`` on the same connection
    (valid for SERIAL/IDENTITY columns within the current transaction). If no
    sequence was touched, fall back to ``rowcount``.
    """
    if result.lastrowid:
        return result.lastrowid
    if conn.dialect.name == "postgresql":
        try:
            value = conn.execute(text("SELECT lastval()")).scalar()
        except (OperationalError, ProgrammingError):
            return result.rowcount
        if value is not None:
            return int(value)
    return result.rowcount


class SqlAlchemyQueryExecutor(DatabaseQueryExecutorInterface):
    """Execute queries using SQLAlchemy Core (connection-per-call, no ORM).

    .. note:: SQLite in-memory databases

        When using ``sqlite:///:memory:`` in tests, each new connection receives
        a separate empty database.  To share one in-memory DB across all
        connections (including ``setup_db`` / schema creation) use
        ``StaticPool``::

            from sqlalchemy.pool import StaticPool

            engine = create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @property
    def engine(self) -> Engine:
        """Underlying SQLAlchemy engine. Useful for teardown: ``executor.engine.dispose()``."""
        return self._engine

    def fetch_all(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                return [dict(row._mapping) for row in result]
        except OperationalError as exc:
            raise DatabaseConnectionException(str(exc)) from exc

    def fetch_one(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                row = result.fetchone()
                return dict(row._mapping) if row else None
        except OperationalError as exc:
            raise DatabaseConnectionException(str(exc)) from exc

    def write(self, sql: str, params: dict[str, Any] | None = None) -> int:
        """Execute INSERT / UPDATE / DELETE and return a meaningful int.

        Return value semantics:
        - INSERT with AUTOINCREMENT/SERIAL column → ``lastrowid`` (the new row's PK, always > 0)
        - INSERT without auto-PK, or multi-row INSERT → ``rowcount``
        - UPDATE / DELETE → ``rowcount`` (number of rows affected; 0 means nothing matched)

        Use the return value to detect missing rows::

            affected = executor.write("UPDATE ... WHERE id = :id", {"id": pk})
            if affected == 0:
                raise NotFoundException(pk)
        """
        try:
            with self._engine.begin() as conn:
                result = conn.execute(text(sql), params or {})
                if sql.strip().upper().startswith("INSERT"):
                    return _insert_id(conn, result)
                return result.rowcount
        except IntegrityError as exc:
            raise DatabaseIntegrityException(str(exc)) from exc
        except OperationalError as exc:
            raise DatabaseConnectionException(str(exc)) from exc


class _BoundQueryExecutor(DatabaseQueryExecutorInterface):
    """Query executor bound to an existing connection (within a transaction)."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def fetch_all(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        try:
            result = self._conn.execute(text(sql), params or {})
            return [dict(row._mapping) for row in result]
        except OperationalError as exc:
            raise DatabaseConnectionException(str(exc)) from exc

    def fetch_one(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        try:
            result = self._conn.execute(text(sql), params or {})
            row = result.fetchone()
            return dict(row._mapping) if row else None
        except OperationalError as exc:
            raise DatabaseConnectionException(str(exc)) from exc

    def write(self, sql: str, params: dict[str, Any] | None = None) -> int:
        try:
            result = self._conn.execute(text(sql), params or {})
        except IntegrityError as exc:
            raise DatabaseIntegrityException(str(exc)) from exc
        except OperationalError as exc:
            raise DatabaseConnectionException(str(exc)) from exc
        if sql.strip().upper().startswith("INSERT"):
            return _insert_id(self._conn, result)
        return result.rowcount


class SqlAlchemyTransactionManager(DatabaseTransactionManagerInterface):
    """Manage database transactions using SQLAlchemy.

    Use transactional() for the recommended callback-based API.
    Use begin() / commit() / rollback() for explicit transaction control.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._conn: Connection | None = None
        # reason: RootTransaction is an internal SQLAlchemy type not exported in the public API
        self._tx: Any = None

    @property
    def engine(self) -> Engine:
        """Underlying SQLAlchemy engine. Useful for teardown: ``manager.engine.dispose()``."""
        return self._engine

    def transactional[T](self, callback: Callable[[DatabaseQueryExecutorInterface], T]) -> T:
        try:
            with self._engine.begin() as conn:
                return callback(_BoundQueryExecutor(conn))
        except DatabaseIntegrityException:
            raise
        except IntegrityError as exc:
            raise DatabaseIntegrityException(str(exc)) from exc
        except OperationalError as exc:
            raise DatabaseConnectionException(str(exc)) from exc

    def begin(self) -> None:
        self._conn = self._engine.connect()
        self._tx = self._conn.begin()

    def commit(self) -> None:
        if self._tx is not None:
            self._tx.commit()
            self._tx = None
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def rollback(self) -> None:
        if self._tx is not None:
            self._tx.rollback()
            self._tx = None
        if self._conn is not None:
            self._conn.close()
            self._conn = None
