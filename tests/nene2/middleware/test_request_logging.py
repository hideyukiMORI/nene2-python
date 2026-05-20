"""Tests for RequestLoggingMiddleware."""

import structlog
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


def test_extra_context_is_bound_to_structlog() -> None:
    captured: list[dict] = []
    app = FastAPI()
    app.add_middleware(
        RequestLoggingMiddleware,
        extra_context={"service": "my-api", "version": "1.0"},
    )
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping() -> JSONResponse:
        captured.append(dict(structlog.contextvars.get_contextvars()))
        return JSONResponse({"ok": True})

    client = TestClient(app)
    client.get("/ping")
    assert captured[0]["service"] == "my-api"
    assert captured[0]["version"] == "1.0"


def test_extra_context_default_is_empty() -> None:
    captured: list[dict] = []
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)  # extra_context なし
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping() -> JSONResponse:
        captured.append(dict(structlog.contextvars.get_contextvars()))
        return JSONResponse({"ok": True})

    client = TestClient(app)
    client.get("/ping")
    assert "service" not in captured[0]


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


def test_context_extractor_adds_dynamic_context() -> None:
    """context_extractor が返した値がログコンテキストに含まれる。"""
    captured: list[dict] = []
    app = FastAPI()
    app.add_middleware(
        RequestLoggingMiddleware,
        context_extractor=lambda req: {"user_id": req.headers.get("X-User-Id", "anon")},
    )
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping() -> JSONResponse:
        captured.append(dict(structlog.contextvars.get_contextvars()))
        return JSONResponse({"ok": True})

    client = TestClient(app)
    client.get("/ping", headers={"X-User-Id": "user-42"})
    assert captured[0]["user_id"] == "user-42"


def test_context_extractor_default_is_none() -> None:
    """context_extractor を省略した場合は従来通り動作する。"""
    captured: list[dict] = []
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping() -> JSONResponse:
        captured.append(dict(structlog.contextvars.get_contextvars()))
        return JSONResponse({"ok": True})

    client = TestClient(app)
    client.get("/ping")
    assert "user_id" not in captured[0]


def test_context_extractor_exception_is_silently_skipped() -> None:
    """context_extractor が例外を投げてもリクエスト処理が続行される。"""
    app = FastAPI()

    def _exploding_extractor(req: object) -> dict[str, str]:
        raise RuntimeError("extractor failure")

    app.add_middleware(RequestLoggingMiddleware, context_extractor=_exploding_extractor)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/ping")
    assert r.status_code == 200  # ログの失敗がリクエスト処理を壊さない


def test_context_extractor_merges_with_extra_context() -> None:
    """context_extractor と extra_context が両方指定されても正しくマージされる。"""
    captured: list[dict] = []
    app = FastAPI()
    app.add_middleware(
        RequestLoggingMiddleware,
        extra_context={"service": "my-api"},
        context_extractor=lambda req: {"user_id": "user-1"},
    )
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping() -> JSONResponse:
        captured.append(dict(structlog.contextvars.get_contextvars()))
        return JSONResponse({"ok": True})

    client = TestClient(app)
    client.get("/ping")
    assert captured[0]["service"] == "my-api"
    assert captured[0]["user_id"] == "user-1"
