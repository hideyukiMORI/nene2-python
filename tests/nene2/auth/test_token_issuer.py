"""Tests for TokenIssuerProtocol and TokenVerificationException."""

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.auth import (
    BearerTokenMiddleware,
    TokenIssuerProtocol,
    TokenVerificationException,
    TokenVerifierProtocol,
)


class _StubIssuer:
    """Minimal TokenIssuerProtocol implementation for testing."""

    def issue(self, claims: dict[str, object]) -> str:
        return f"stub-token-{claims.get('sub', 'anon')}"


class _RaisingVerifier:
    """Verifier that raises TokenVerificationException."""

    def verify(self, token: str) -> bool:
        raise TokenVerificationException("token expired")


def test_stub_issuer_satisfies_protocol() -> None:
    assert isinstance(_StubIssuer(), TokenIssuerProtocol)


def test_stub_issuer_returns_token_string() -> None:
    token = _StubIssuer().issue({"sub": "user-1"})
    assert isinstance(token, str)
    assert "user-1" in token


def test_token_verification_exception_is_exception() -> None:
    with pytest.raises(TokenVerificationException):
        raise TokenVerificationException("bad token")


def test_raising_verifier_satisfies_verifier_protocol() -> None:
    assert isinstance(_RaisingVerifier(), TokenVerifierProtocol)


def test_bearer_middleware_maps_token_verification_exception_to_401() -> None:
    app = FastAPI()
    app.add_middleware(BearerTokenMiddleware, verifier=_RaisingVerifier())

    @app.get("/secret")
    async def secret() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/secret", headers={"Authorization": "Bearer any-token"})
    assert response.status_code == 401
    assert response.json()["type"].endswith("unauthorized")
