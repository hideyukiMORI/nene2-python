"""Tests for ErrorHandlerMiddleware."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response
from nene2.middleware import DomainExceptionHandlerProtocol, ErrorHandlerMiddleware
from nene2.middleware.error_handler import request_validation_error_handler
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


def _make_app_with_pydantic_handler() -> FastAPI:
    class _Body(BaseModel):
        rating: int = Field(ge=1, le=5)
        price: int = Field(ge=0)

    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_exception_handler(
        RequestValidationError,
        request_validation_error_handler,  # type: ignore[arg-type]
    )

    @app.post("/items")
    async def create_item(body: _Body) -> JSONResponse:
        return JSONResponse({"rating": body.rating, "price": body.price})

    return app


def test_pydantic_validation_error_returns_problem_details_format() -> None:
    client = TestClient(_make_app_with_pydantic_handler(), raise_server_exceptions=False)
    r = client.post("/items", json={"rating": 99, "price": -1})
    assert r.status_code == 422
    body = r.json()
    assert body["type"].endswith("validation-failed")
    assert body["status"] == 422
    assert isinstance(body["errors"], list)
    assert len(body["errors"]) == 2


def test_pydantic_validation_error_field_names_are_extracted() -> None:
    client = TestClient(_make_app_with_pydantic_handler(), raise_server_exceptions=False)
    r = client.post("/items", json={"rating": 99, "price": 100})
    assert r.status_code == 422
    fields = [e["field"] for e in r.json()["errors"]]
    assert "rating" in fields
