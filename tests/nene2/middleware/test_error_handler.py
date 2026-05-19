"""Tests for ErrorHandlerMiddleware."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.middleware import ErrorHandlerMiddleware
from nene2.validation.exceptions import ValidationError, ValidationException


def _make_app(*, debug: bool = False) -> FastAPI:
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware, debug=debug)
    app.add_exception_handler(
        ValidationException,
        ErrorHandlerMiddleware.handle_validation_exception,  # type: ignore[arg-type]
    )

    @app.get("/boom")
    async def boom() -> JSONResponse:
        raise RuntimeError("secret internal detail")

    @app.get("/validation-error")
    async def validation_error() -> JSONResponse:
        raise ValidationException([ValidationError("field", "bad value", "invalid")])

    return app


def test_unhandled_exception_returns_500() -> None:
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.get("/boom")
    assert r.status_code == 500
    assert r.json()["type"].endswith("internal-server-error")


def test_debug_mode_exposes_exception_message() -> None:
    client = TestClient(_make_app(debug=True), raise_server_exceptions=False)
    r = client.get("/boom")
    assert "secret internal detail" in r.json()["detail"]


def test_non_debug_mode_hides_exception_message() -> None:
    client = TestClient(_make_app(debug=False), raise_server_exceptions=False)
    r = client.get("/boom")
    assert "secret internal detail" not in r.json().get("detail", "")


def test_validation_exception_returns_422() -> None:
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.get("/validation-error")
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "field"
