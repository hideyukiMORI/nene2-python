"""Tests for CORS configuration via AppSettings."""

from fastapi.testclient import TestClient

from example.app import create_app
from nene2.config import AppSettings


def test_cors_disabled_by_default() -> None:
    cfg = AppSettings(throttle_enabled=False)
    client = TestClient(create_app(cfg))
    response = client.get("/health", headers={"Origin": "http://example.com"})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_cors_enabled_returns_allow_origin() -> None:
    cfg = AppSettings(
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        throttle_enabled=False,
    )
    client = TestClient(create_app(cfg))
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"


def test_cors_preflight_returns_204() -> None:
    cfg = AppSettings(
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        throttle_enabled=False,
    )
    client = TestClient(create_app(cfg))
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code in (200, 204)
    assert "Access-Control-Allow-Origin" in response.headers


def test_cors_preflight_not_blocked_by_throttle() -> None:
    cfg = AppSettings(
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        throttle_enabled=True,
        throttle_limit=1,
        throttle_window=60,
    )
    client = TestClient(create_app(cfg))
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    }
    # First request consumes the one allowed slot.
    client.get("/health", headers={"Origin": "http://localhost:3000"})
    # Preflight OPTIONS must still succeed even though the rate limit is exhausted.
    response = client.options("/health", headers=headers)
    assert response.status_code in (200, 204)
    assert "Access-Control-Allow-Origin" in response.headers
