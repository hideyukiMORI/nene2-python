"""Tests for RequestIdMiddleware."""

import re

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.middleware import RequestIdMiddleware, request_id_var

_UUID_V4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping() -> JSONResponse:
        return JSONResponse({"request_id": request_id_var.get()})

    return app


def test_response_has_x_request_id() -> None:
    client = TestClient(_make_app())
    response = client.get("/ping")
    assert response.status_code == 200
    assert "X-Request-Id" in response.headers
    rid = response.headers["X-Request-Id"]
    assert len(rid) == 36


def test_forwards_valid_uuid_v4_request_id() -> None:
    valid_id = "550e8400-e29b-41d4-a716-446655440000"
    client = TestClient(_make_app())
    response = client.get("/ping", headers={"X-Request-Id": valid_id})
    assert response.headers["X-Request-Id"] == valid_id


def test_invalid_request_id_is_replaced_with_new_uuid() -> None:
    """Non-UUID values must not be forwarded to prevent log injection."""
    client = TestClient(_make_app())
    response = client.get("/ping", headers={"X-Request-Id": "my-trace-id-123"})
    rid = response.headers["X-Request-Id"]
    assert rid != "my-trace-id-123"
    assert _UUID_V4_RE.match(rid), f"Expected UUID v4, got {rid!r}"


def test_newline_in_request_id_is_rejected() -> None:
    """Newlines in X-Request-Id must be rejected to prevent log injection."""
    client = TestClient(_make_app())
    response = client.get("/ping", headers={"X-Request-Id": "abc\nERROR injected"})
    rid = response.headers["X-Request-Id"]
    assert "\n" not in rid
    assert _UUID_V4_RE.match(rid)


def test_request_id_available_in_contextvars() -> None:
    client = TestClient(_make_app())
    response = client.get("/ping")
    body = response.json()
    assert body["request_id"] == response.headers["X-Request-Id"]


def test_each_request_gets_unique_id() -> None:
    client = TestClient(_make_app())
    ids = {client.get("/ping").headers["X-Request-Id"] for _ in range(5)}
    assert len(ids) == 5
