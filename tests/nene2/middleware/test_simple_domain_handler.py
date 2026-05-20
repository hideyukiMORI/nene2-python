"""Tests for SimpleDomainHandler."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.middleware import ErrorHandlerMiddleware, SimpleDomainHandler
from nene2.middleware.domain_exception import DomainExceptionHandlerProtocol


class _NotFoundError(Exception):
    def __init__(self, resource_id: int) -> None:
        self.resource_id = resource_id
        super().__init__(f"Resource {resource_id} not found")


class _AccessDeniedError(Exception):
    pass


def _make_app(*handlers: DomainExceptionHandlerProtocol) -> FastAPI:
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware, domain_handlers=list(handlers))

    @app.get("/not-found")
    async def raise_not_found() -> JSONResponse:
        raise _NotFoundError(42)

    @app.get("/access-denied")
    async def raise_access_denied() -> JSONResponse:
        raise _AccessDeniedError("forbidden")

    return app


def test_simple_handler_satisfies_protocol() -> None:
    handler = SimpleDomainHandler(_NotFoundError, "not-found", "Not Found", 404)
    assert isinstance(handler, DomainExceptionHandlerProtocol)


def test_simple_handler_handles_correct_exception_class() -> None:
    handler = SimpleDomainHandler(_NotFoundError, "not-found", "Not Found", 404)
    assert handler.handles(_NotFoundError(1)) is True
    assert handler.handles(_AccessDeniedError()) is False


def test_simple_handler_returns_problem_details_response() -> None:
    handler = SimpleDomainHandler(_NotFoundError, "not-found", "Not Found", 404)
    client = TestClient(_make_app(handler), raise_server_exceptions=False)
    r = client.get("/not-found")
    assert r.status_code == 404
    body = r.json()
    assert "not-found" in body["type"]
    assert body["status"] == 404
    assert "problem+json" in r.headers["content-type"]


def test_simple_handler_with_static_detail() -> None:
    handler = SimpleDomainHandler(
        _NotFoundError, "not-found", "Not Found", 404, detail="Resource missing"
    )
    client = TestClient(_make_app(handler), raise_server_exceptions=False)
    r = client.get("/not-found")
    assert r.json()["detail"] == "Resource missing"


def test_simple_handler_with_detail_factory() -> None:
    handler = SimpleDomainHandler(
        _NotFoundError,
        "not-found",
        "Not Found",
        404,
        detail_factory=str,
    )
    client = TestClient(_make_app(handler), raise_server_exceptions=False)
    r = client.get("/not-found")
    assert "Resource 42 not found" in r.json()["detail"]


def test_simple_handler_with_extra_factory() -> None:
    handler = SimpleDomainHandler(
        _NotFoundError,
        "not-found",
        "Not Found",
        404,
        extra_factory=lambda exc: {"resource_id": exc.resource_id},  # type: ignore[union-attr]
    )
    client = TestClient(_make_app(handler), raise_server_exceptions=False)
    r = client.get("/not-found")
    assert r.json()["resource_id"] == 42


def test_multiple_simple_handlers_registered_together() -> None:
    handlers = [
        SimpleDomainHandler(_NotFoundError, "not-found", "Not Found", 404),
        SimpleDomainHandler(_AccessDeniedError, "access-denied", "Access Denied", 403),
    ]
    client = TestClient(_make_app(*handlers), raise_server_exceptions=False)
    assert client.get("/not-found").status_code == 404
    assert client.get("/access-denied").status_code == 403
