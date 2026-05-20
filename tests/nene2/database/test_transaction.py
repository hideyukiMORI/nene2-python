"""Tests for SqlAlchemyTransactionManager — transactional() and begin/commit/rollback."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from nene2.database import (
    DatabaseIntegrityException,
    DatabaseQueryExecutorInterface,
    SqlAlchemyTransactionManager,
)


def _manager() -> SqlAlchemyTransactionManager:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    manager = SqlAlchemyTransactionManager(engine)
    manager.transactional(
        lambda ex: ex.write(
            "CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)"
        )
    )
    return manager


def test_transactional_commits_on_success() -> None:
    mgr = _manager()

    def insert(ex: DatabaseQueryExecutorInterface) -> int:
        return ex.write("INSERT INTO items (name) VALUES (:name)", {"name": "hello"})

    mgr.transactional(insert)
    rows = mgr.transactional(lambda ex: ex.fetch_all("SELECT * FROM items"))
    assert len(rows) == 1
    assert rows[0]["name"] == "hello"


def test_transactional_rollback_on_exception() -> None:
    mgr = _manager()

    def failing(ex: DatabaseQueryExecutorInterface) -> None:
        ex.write("INSERT INTO items (name) VALUES (:name)", {"name": "will-rollback"})
        raise ValueError("intentional failure")

    with pytest.raises(ValueError):
        mgr.transactional(failing)

    rows = mgr.transactional(lambda ex: ex.fetch_all("SELECT * FROM items"))
    assert rows == []


def test_transactional_returns_callback_value() -> None:
    mgr = _manager()
    mgr.transactional(lambda ex: ex.write("INSERT INTO items (name) VALUES ('x')"))
    count = mgr.transactional(lambda ex: ex.fetch_one("SELECT COUNT(*) AS cnt FROM items"))
    assert count is not None
    assert count["cnt"] == 1


def test_begin_commit_workflow() -> None:
    mgr = _manager()
    mgr.begin()
    mgr.transactional(lambda ex: ex.write("INSERT INTO items (name) VALUES ('low-level')"))
    mgr.commit()
    rows = mgr.transactional(lambda ex: ex.fetch_all("SELECT * FROM items"))
    assert any(r["name"] == "low-level" for r in rows)


def test_begin_rollback_workflow() -> None:
    mgr = _manager()
    mgr.begin()
    mgr.rollback()
    rows = mgr.transactional(lambda ex: ex.fetch_all("SELECT * FROM items"))
    assert rows == []


def test_transactional_raises_database_integrity_exception_on_unique_violation() -> None:
    mgr = _manager()
    mgr.transactional(lambda ex: ex.write("INSERT INTO items (name) VALUES ('dup')"))

    def _duplicate(ex: DatabaseQueryExecutorInterface) -> None:
        ex.write("INSERT INTO items (name) VALUES ('dup')")

    with pytest.raises(DatabaseIntegrityException):
        mgr.transactional(_duplicate)


def test_transactional_rollback_on_integrity_error() -> None:
    mgr = _manager()

    def _partial_then_fail(ex: DatabaseQueryExecutorInterface) -> None:
        ex.write("INSERT INTO items (name) VALUES ('first')")
        ex.write("INSERT INTO items (name) VALUES ('first')")  # UNIQUE violation

    with pytest.raises(DatabaseIntegrityException):
        mgr.transactional(_partial_then_fail)

    rows = mgr.transactional(lambda ex: ex.fetch_all("SELECT * FROM items"))
    assert rows == []  # ロールバックされて何も残っていない
