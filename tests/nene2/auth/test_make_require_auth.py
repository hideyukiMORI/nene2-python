"""Tests for make_require_auth() Depends factory."""

from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.auth import LocalTokenVerifier, make_require_auth


def _make_app(tokens: list[str]) -> FastAPI:
    verifier = LocalTokenVerifier(tokens)
    require_auth = make_require_auth(verifier)

    app = FastAPI()

    @app.get("/public")
    def public() -> JSONResponse:
        return JSONResponse({"public": True})

    @app.get("/protected")
    def protected(token: Annotated[str, Depends(require_auth)]) -> JSONResponse:
        return JSONResponse({"token": token})

    @app.post("/items")
    def create(token: Annotated[str, Depends(require_auth)]) -> JSONResponse:
        return JSONResponse({"created_by": token[:8]}, status_code=201)

    return app


def test_valid_token_returns_200() -> None:
    client = TestClient(_make_app(["secret-token"]), raise_server_exceptions=False)
    r = client.get("/protected", headers={"Authorization": "Bearer secret-token"})
    assert r.status_code == 200
    assert r.json()["token"] == "secret-token"  # noqa: S105


def test_missing_token_returns_401() -> None:
    client = TestClient(_make_app(["secret-token"]), raise_server_exceptions=False)
    r = client.get("/protected")
    assert r.status_code == 401


def test_invalid_token_returns_401() -> None:
    client = TestClient(_make_app(["secret-token"]), raise_server_exceptions=False)
    r = client.get("/protected", headers={"Authorization": "Bearer wrong-token"})
    assert r.status_code == 401


def test_public_endpoint_no_auth_required() -> None:
    client = TestClient(_make_app([]), raise_server_exceptions=False)
    r = client.get("/public")
    assert r.status_code == 200


def test_post_with_valid_token_returns_201() -> None:
    client = TestClient(_make_app(["my-api-key"]), raise_server_exceptions=False)
    r = client.post("/items", headers={"Authorization": "Bearer my-api-key"})
    assert r.status_code == 201


def test_multiple_valid_tokens() -> None:
    client = TestClient(_make_app(["token-a", "token-b"]), raise_server_exceptions=False)
    r_a = client.get("/protected", headers={"Authorization": "Bearer token-a"})
    r_b = client.get("/protected", headers={"Authorization": "Bearer token-b"})
    assert r_a.status_code == 200
    assert r_b.status_code == 200


def test_empty_allowlist_rejects_all() -> None:
    client = TestClient(_make_app([]), raise_server_exceptions=False)
    r = client.get("/protected", headers={"Authorization": "Bearer any-token"})
    assert r.status_code == 401


def test_different_verifiers_independent() -> None:
    """2つの異なる verifier を同じアプリで使える。"""
    verifier_a = LocalTokenVerifier(["token-a"])
    verifier_b = LocalTokenVerifier(["token-b"])
    require_a = make_require_auth(verifier_a)
    require_b = make_require_auth(verifier_b)

    app = FastAPI()

    @app.get("/route-a")
    def route_a(token: Annotated[str, Depends(require_a)]) -> JSONResponse:
        return JSONResponse({"token": token})

    @app.get("/route-b")
    def route_b(token: Annotated[str, Depends(require_b)]) -> JSONResponse:
        return JSONResponse({"token": token})

    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/route-a", headers={"Authorization": "Bearer token-a"}).status_code == 200
    assert client.get("/route-a", headers={"Authorization": "Bearer token-b"}).status_code == 401
    assert client.get("/route-b", headers={"Authorization": "Bearer token-b"}).status_code == 200
    assert client.get("/route-b", headers={"Authorization": "Bearer token-a"}).status_code == 401
