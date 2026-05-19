"""Database abstraction interfaces.

Equivalent to PHP Nene2\\Database\\DatabaseQueryExecutorInterface
and DatabaseTransactionManagerInterface.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class DatabaseQueryExecutorInterface(ABC):
    """Execute parameterised SQL queries against a database."""

    @abstractmethod
    def fetch_all(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def fetch_one(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None: ...

    @abstractmethod
    def write(self, sql: str, params: dict[str, Any] | None = None) -> int:
        """Execute INSERT / UPDATE / DELETE.

        Returns lastrowid for INSERT, affected rowcount for UPDATE/DELETE.
        """
        ...


class DatabaseTransactionManagerInterface(ABC):
    """Manage database transactions.

    High-level API: use transactional() — it commits on success and rolls back on exception.
    Low-level API: begin() / commit() / rollback() for manual control.
    """

    @abstractmethod
    def transactional[T](
        self, callback: Callable[[DatabaseQueryExecutorInterface], T]
    ) -> T:
        """Run callback inside a transaction; commit on success, rollback on exception."""
        ...

    @abstractmethod
    def begin(self) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
