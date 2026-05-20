"""Tests for CORS configuration via AppSettings."""

from collections.abc import Generator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from example.app import create_app
from nene2.config import AppSettings
from nene2.database import SqlAlchemyQueryExecutor


@contextmanager
def _make_client(cfg: AppSettings) -> Generator[TestClient, None, None]:
    app = create_app(cfg)
    yield TestClient(app)
    executor = getattr(app.state, "db_executor", None)
    if isinstance(executor, SqlAlchemyQueryExecutor):
        executor.engine.dispose()


def test_cors_disabled_by_default() -> None:
    with _make_client(AppSettings(throttle_enabled=False)) as client:
        response = client.get("/health", headers={"Origin": "http://example.com"})
        assert "Access-Control-Allow-Origin" not in response.headers


def test_cors_enabled_returns_allow_origin() -> None:
    cfg = AppSettings(
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        throttle_enabled=False,
    )
    with _make_client(cfg) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"


def test_cors_preflight_returns_204() -> None:
    cfg = AppSettings(
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        throttle_enabled=False,
    )
    with _make_client(cfg) as client:
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
    with _make_client(cfg) as client:
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
