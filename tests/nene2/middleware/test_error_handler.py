"""Tests for ErrorHandlerMiddleware."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response
from nene2.middleware import DomainExceptionHandlerProtocol, ErrorHandlerMiddleware
from nene2.validation.exceptions import ValidationError, ValidationException


class _DomainError(Exception):
    pass


class _DomainErrorHandler:
    def handles(self, exc: Exception) -> bool:
        return isinstance(exc, _DomainError)

    def handle(self, exc: Exception) -> Response:
        return problem_details_response("domain-error", "Domain Error", 409)


def _make_app(
    *, debug: bool = False, domain_handlers: list[DomainExceptionHandlerProtocol] | None = None
) -> FastAPI:
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware, debug=debug, domain_handlers=domain_handlers)
    app.add_exception_handler(
        ValidationException,
        ErrorHandlerMiddleware.handle_validation_exception,  # type: ignore[arg-type]
    )

    @app.get("/boom")
    async def boom() -> JSONResponse:
        raise RuntimeError("secret internal detail")

    @app.get("/domain-error")
    async def domain_error() -> JSONResponse:
        raise _DomainError()

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


def test_domain_exception_handler_returns_mapped_status() -> None:
    client = TestClient(
        _make_app(domain_handlers=[_DomainErrorHandler()]), raise_server_exceptions=False
    )
    r = client.get("/domain-error")
    assert r.status_code == 409
    assert r.json()["type"].endswith("domain-error")


def test_unregistered_domain_exception_falls_through_to_500() -> None:
    client = TestClient(_make_app(domain_handlers=[]), raise_server_exceptions=False)
    r = client.get("/domain-error")
    assert r.status_code == 500
