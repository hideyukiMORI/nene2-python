"""Shared fixtures for example HTTP integration tests."""

import pytest
from fastapi.testclient import TestClient

from example.app import create_app
from nene2.config import AppSettings


@pytest.fixture
def client() -> TestClient:
    """Fresh TestClient with in-memory DB and throttle disabled (per-test isolation)."""
    return TestClient(create_app(AppSettings(throttle_enabled=False)))
