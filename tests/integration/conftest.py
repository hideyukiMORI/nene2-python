"""Fixtures for real-database integration tests.

These tests exercise SqlAlchemyQueryExecutor against actual PostgreSQL / MySQL
servers — the dialects the framework claims to support but only ever tested on
SQLite. They run only when the corresponding URL env var is set, so the default
``uv run pytest`` stays SQLite-only and fast. CI sets the env vars via service
containers (see .github/workflows/ci.yml).
"""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, Text, create_engine

from nene2.database import SqlAlchemyQueryExecutor

# backend name -> env var holding its SQLAlchemy URL
_BACKEND_ENV: dict[str, str] = {
    "postgresql": "NENE2_TEST_POSTGRES_URL",
    "mysql": "NENE2_TEST_MYSQL_URL",
}

# Dialect-portable schema. SQLAlchemy emits SERIAL (PostgreSQL) / AUTO_INCREMENT
# (MySQL) from the same Integer autoincrement PK — no hand-written per-dialect DDL.
_metadata = MetaData()
Table(
    "notes",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("title", Text, nullable=False),
    Column("body", Text, nullable=False),
)


def _configured_backends() -> list[str]:
    return [name for name, env in _BACKEND_ENV.items() if os.environ.get(env)]


def _params() -> list[object]:
    backends = _configured_backends()
    if backends:
        return list(backends)
    reason = "no real DB configured (set NENE2_TEST_POSTGRES_URL / NENE2_TEST_MYSQL_URL)"
    return [pytest.param(None, marks=pytest.mark.skip(reason=reason))]


@pytest.fixture(params=_params())
def real_db_executor(request: pytest.FixtureRequest) -> Iterator[SqlAlchemyQueryExecutor]:
    backend: str = request.param
    engine = create_engine(os.environ[_BACKEND_ENV[backend]])
    _metadata.drop_all(engine)
    _metadata.create_all(engine)
    try:
        yield SqlAlchemyQueryExecutor(engine)
    finally:
        _metadata.drop_all(engine)
        engine.dispose()
