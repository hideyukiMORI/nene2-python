"""Tests for RequestIdMiddleware."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.middleware import RequestIdMiddleware, request_id_var


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
    assert len(rid) == 36  # UUID v4 format


def test_forwards_provided_request_id() -> None:
    client = TestClient(_make_app())
    response = client.get("/ping", headers={"X-Request-Id": "my-trace-id-123"})
    assert response.headers["X-Request-Id"] == "my-trace-id-123"


def test_request_id_available_in_contextvars() -> None:
    client = TestClient(_make_app())
    response = client.get("/ping")
    body = response.json()
    assert body["request_id"] == response.headers["X-Request-Id"]


def test_each_request_gets_unique_id() -> None:
    client = TestClient(_make_app())
    ids = {client.get("/ping").headers["X-Request-Id"] for _ in range(5)}
    assert len(ids) == 5
