"""Shared fixtures for example HTTP integration tests."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from example.app import create_app
from nene2.config import AppSettings
from nene2.database import SqlAlchemyQueryExecutor


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Fresh TestClient with in-memory DB and throttle disabled (per-test isolation)."""
    app = create_app(AppSettings(throttle_enabled=False))
    yield TestClient(app)
    executor = getattr(app.state, "db_executor", None)
    if isinstance(executor, SqlAlchemyQueryExecutor):
        executor.engine.dispose()
