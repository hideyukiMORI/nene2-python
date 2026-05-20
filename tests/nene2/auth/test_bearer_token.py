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


def test_local_verifier_accepts_set() -> None:
    verifier = LocalTokenVerifier({"tok-a", "tok-b"})
    assert verifier.verify("tok-a") is True
    assert verifier.verify("tok-b") is True
    assert verifier.verify("tok-c") is False


def test_local_verifier_accepts_frozenset() -> None:
    verifier = LocalTokenVerifier(frozenset({"tok-x", "tok-y"}))
    assert verifier.verify("tok-x") is True
    assert verifier.verify("unknown") is False


# ---------------------------------------------------------------------------
# include_paths tests
# ---------------------------------------------------------------------------
def _make_app_with_include_paths(tokens: list[str], include_paths: list[str]) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        BearerTokenMiddleware,
        verifier=LocalTokenVerifier(tokens),
        include_paths=include_paths,
    )

    @app.get("/admin/dashboard")
    async def admin_dashboard() -> JSONResponse:
        return JSONResponse({"admin": True})

    @app.get("/public/hello")
    async def public_hello() -> JSONResponse:
        return JSONResponse({"hello": True})

    return app


def test_include_paths_protects_matching_prefix() -> None:
    client = TestClient(_make_app_with_include_paths(["tok"], ["/admin"]))
    assert client.get("/admin/dashboard").status_code == 401
    assert (
        client.get("/admin/dashboard", headers={"Authorization": "Bearer tok"}).status_code == 200
    )


def test_include_paths_skips_non_matching_prefix() -> None:
    """include_paths にないパスは認証なしで通過する。"""
    client = TestClient(_make_app_with_include_paths(["tok"], ["/admin"]))
    assert client.get("/public/hello").status_code == 200


def test_include_paths_multiple_prefixes() -> None:
    app = FastAPI()
    app.add_middleware(
        BearerTokenMiddleware,
        verifier=LocalTokenVerifier(["tok"]),
        include_paths=["/admin", "/private"],
    )

    @app.get("/admin/x")
    async def admin_x() -> JSONResponse:
        return JSONResponse({"ok": True})

    @app.get("/private/y")
    async def private_y() -> JSONResponse:
        return JSONResponse({"ok": True})

    @app.get("/public/z")
    async def public_z() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    assert client.get("/admin/x").status_code == 401
    assert client.get("/private/y").status_code == 401
    assert client.get("/public/z").status_code == 200


def test_include_paths_takes_precedence_over_exclude_paths() -> None:
    """両方指定されたときは include_paths が優先される。"""
    app = FastAPI()
    app.add_middleware(
        BearerTokenMiddleware,
        verifier=LocalTokenVerifier(["tok"]),
        include_paths=["/admin"],
        exclude_paths=["/admin/open"],  # include_paths があるので無視される
    )

    @app.get("/admin/open")
    async def admin_open() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    # include_paths=["/admin"] が優先 → /admin/open も保護される
    assert client.get("/admin/open").status_code == 401
