"""Tests for RequestLoggingMiddleware."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.middleware import RequestIdMiddleware, RequestLoggingMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping() -> JSONResponse:
        return JSONResponse({"ok": True})

    @app.get("/fail")
    async def fail() -> JSONResponse:
        return JSONResponse({}, status_code=500)

    return app


def test_request_passes_through() -> None:
    client = TestClient(_make_app())
    response = client.get("/ping")
    assert response.status_code == 200


def test_error_response_passes_through() -> None:
    client = TestClient(_make_app())
    response = client.get("/fail")
    assert response.status_code == 500


def test_logging_does_not_remove_headers() -> None:
    client = TestClient(_make_app())
    response = client.get("/ping")
    assert "X-Request-Id" in response.headers


def test_exclude_paths_passes_requests_through() -> None:
    """exclude_paths に指定したパスへのリクエストがミドルウェアを通過すること"""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware, exclude_paths=["/health"])
    app.add_middleware(RequestIdMiddleware)

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/items")
    async def items() -> JSONResponse:
        return JSONResponse([])

    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/items").status_code == 200
