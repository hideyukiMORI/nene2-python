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


def test_local_verifier_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_TOKENS", "tok-a,tok-b, tok-c ")
    verifier = LocalTokenVerifier.from_env("TEST_TOKENS")
    assert verifier.verify("tok-a") is True
    assert verifier.verify("tok-c") is True
    assert verifier.verify("tok-d") is False


def test_local_verifier_from_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_TOKENS", raising=False)
    verifier = LocalTokenVerifier.from_env("TEST_TOKENS")
    assert verifier.verify("anything") is False


def test_local_verifier_from_env_custom_separator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_TOKENS", "tok-a|tok-b")
    verifier = LocalTokenVerifier.from_env("TEST_TOKENS", separator="|")
    assert verifier.verify("tok-a") is True
    assert verifier.verify("tok-b") is True


def test_exclude_paths_bypasses_auth() -> None:
    app = FastAPI()
    app.add_middleware(
        BearerTokenMiddleware,
        verifier=LocalTokenVerifier(["tok"]),
        exclude_paths=["/health", "/docs"],
    )

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/secret")
    async def secret() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/secret").status_code == 401
    assert client.get("/secret", headers={"Authorization": "Bearer tok"}).status_code == 200


def test_exclude_paths_default_is_empty() -> None:
    app = FastAPI()
    app.add_middleware(BearerTokenMiddleware, verifier=LocalTokenVerifier(["tok"]))

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    client = TestClient(app)
    assert client.get("/health").status_code == 401
