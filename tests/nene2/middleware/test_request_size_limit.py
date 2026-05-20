"""Tests for RequestSizeLimitMiddleware."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.middleware import RequestSizeLimitMiddleware


def _make_app(max_bytes: int = 100) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=max_bytes)

    @app.post("/upload")
    async def upload() -> JSONResponse:
        return JSONResponse({"ok": True})

    return app


def test_small_request_passes() -> None:
    client = TestClient(_make_app(max_bytes=1000))
    response = client.post(
        "/upload",
        content=b"x" * 50,
        headers={"Content-Length": "50", "Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 200


def test_oversized_request_returns_413() -> None:
    client = TestClient(_make_app(max_bytes=100))
    response = client.post(
        "/upload",
        content=b"x" * 200,
        headers={"Content-Length": "200", "Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 413
    body = response.json()
    assert body["type"].endswith("payload-too-large")


def test_no_content_length_passes() -> None:
    client = TestClient(_make_app(max_bytes=10_000))
    response = client.post("/upload", json={"data": "small"})
    assert response.status_code == 200


def test_oversized_body_without_content_length_returns_413() -> None:
    """Chunked-transfer (no Content-Length) must also be caught."""
    client = TestClient(_make_app(max_bytes=100))
    response = client.post(
        "/upload",
        content=b"x" * 200,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 413


def test_malformed_content_length_is_tolerated() -> None:
    """Non-integer Content-Length header must not crash the middleware."""
    client = TestClient(_make_app(max_bytes=1000))
    response = client.post(
        "/upload",
        content=b"hello",
        headers={"Content-Length": "abc", "Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 200


def test_exclude_paths_bypasses_size_limit() -> None:
    app = FastAPI()
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_bytes=10,
        exclude_paths=["/upload/large"],
    )

    @app.post("/upload")
    async def upload() -> JSONResponse:
        return JSONResponse({"ok": True})

    @app.post("/upload/large")
    async def upload_large() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    assert client.post("/upload", content=b"x" * 100).status_code == 413
    assert client.post("/upload/large", content=b"x" * 100).status_code == 200
