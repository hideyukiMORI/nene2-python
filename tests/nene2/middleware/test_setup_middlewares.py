"""Tests for setup_middlewares()."""

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from nene2.middleware import SimpleDomainHandler, setup_middlewares


class _DomainError(Exception):
    pass


def _make_app(**kwargs: object) -> FastAPI:
    app = FastAPI()
    setup_middlewares(app, **kwargs)  # type: ignore[arg-type]

    @app.get("/ok")
    def ok() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/boom")
    def boom() -> JSONResponse:
        raise RuntimeError("unhandled")

    @app.get("/domain")
    def domain() -> JSONResponse:
        raise _DomainError()

    @app.post("/upload")
    def upload() -> JSONResponse:
        return JSONResponse({"received": True})

    return app


def test_ok_request_returns_200() -> None:
    client = TestClient(_make_app(), raise_server_exceptions=False)
    assert client.get("/ok").status_code == 200


def test_500_is_problem_details() -> None:
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.get("/boom")
    assert r.status_code == 500
    assert r.json()["type"].endswith("internal-server-error")


def test_500_has_request_id() -> None:
    """全エラーレスポンスに X-Request-Id が付く（正しい順序の検証）"""
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.get("/boom")
    assert r.status_code == 500
    assert "X-Request-Id" in r.headers


def test_500_has_security_headers() -> None:
    """全エラーレスポンスにセキュリティヘッダーが付く（正しい順序の検証）"""
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.get("/boom")
    assert r.status_code == 500
    assert "X-Content-Type-Options" in r.headers


def test_413_has_request_id() -> None:
    """サイズ超過エラーにも X-Request-Id が付く"""
    client = TestClient(_make_app(max_request_bytes=10), raise_server_exceptions=False)
    r = client.post("/upload", content=b"x" * 100, headers={"Content-Type": "application/json"})
    assert r.status_code == 413
    assert "X-Request-Id" in r.headers


def test_413_has_security_headers() -> None:
    client = TestClient(_make_app(max_request_bytes=10), raise_server_exceptions=False)
    r = client.post("/upload", content=b"x" * 100, headers={"Content-Type": "application/json"})
    assert r.status_code == 413
    assert "X-Content-Type-Options" in r.headers


def test_throttle_applied_when_limit_set() -> None:
    app = _make_app(throttle_limit=2, throttle_window=60)
    client = TestClient(app, raise_server_exceptions=False)
    client.get("/ok")
    client.get("/ok")
    r = client.get("/ok")
    assert r.status_code == 429


def test_throttle_omitted_when_limit_none() -> None:
    app = _make_app(throttle_limit=None)
    client = TestClient(app, raise_server_exceptions=False)
    for _ in range(10):
        assert client.get("/ok").status_code == 200


def test_domain_handler_via_setup() -> None:
    handlers = [SimpleDomainHandler(_DomainError, "domain-err", "Domain Error", 409)]
    client = TestClient(_make_app(domain_handlers=handlers), raise_server_exceptions=False)
    r = client.get("/domain")
    assert r.status_code == 409


def test_pydantic_422_formatted_as_nene2() -> None:
    class _Body(BaseModel):
        score: int = Field(ge=0, le=10)

    app = FastAPI()
    setup_middlewares(app)

    @app.post("/score")
    def create(body: _Body) -> JSONResponse:
        return JSONResponse({"score": body.score})

    client = TestClient(app, raise_server_exceptions=False)
    r = client.post("/score", json={"score": 999})
    assert r.status_code == 422
    assert r.json()["type"].endswith("validation-failed")


def test_raises_type_error_for_non_starlette_app() -> None:
    with pytest.raises(TypeError, match="Starlette/FastAPI"):
        setup_middlewares(object())
