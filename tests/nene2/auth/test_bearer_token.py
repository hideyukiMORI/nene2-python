"""Tests for BearerTokenMiddleware and LocalTokenVerifier."""

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.auth import BearerTokenMiddleware, LocalTokenVerifier


def _make_app(tokens: list[str]) -> FastAPI:
    app = FastAPI()
    app.add_middleware(BearerTokenMiddleware, verifier=LocalTokenVerifier(tokens))

    @app.get("/secret")
    async def secret() -> JSONResponse:
        return JSONResponse({"ok": True})

    return app


def test_valid_token_returns_200() -> None:
    client = TestClient(_make_app(["valid-token-abc"]))
    response = client.get("/secret", headers={"Authorization": "Bearer valid-token-abc"})
    assert response.status_code == 200


def test_missing_auth_header_returns_401() -> None:
    client = TestClient(_make_app(["valid-token-abc"]))
    response = client.get("/secret")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers
    body = response.json()
    assert body["type"].endswith("unauthorized")


def test_invalid_token_returns_401() -> None:
    client = TestClient(_make_app(["valid-token-abc"]))
    response = client.get("/secret", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401


def test_non_bearer_scheme_returns_401() -> None:
    client = TestClient(_make_app(["valid-token-abc"]))
    response = client.get("/secret", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert response.status_code == 401


@pytest.mark.parametrize("token", ["tok-a", "tok-b", "tok-c"])
def test_multiple_allowed_tokens(token: str) -> None:
    client = TestClient(_make_app(["tok-a", "tok-b", "tok-c"]))
    response = client.get("/secret", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_local_verifier_constant_time() -> None:
    verifier = LocalTokenVerifier(["secret-token"])
    assert verifier.verify("secret-token") is True
    assert verifier.verify("wrong") is False
    assert verifier.verify("") is False
