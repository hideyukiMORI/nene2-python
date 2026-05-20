"""Tests for ApiKeyAuthMiddleware."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.auth import ApiKeyAuthMiddleware, LocalTokenVerifier
from nene2.auth.exceptions import TokenVerificationException


def _make_app(keys: list[str]) -> FastAPI:
    app = FastAPI()
    app.add_middleware(ApiKeyAuthMiddleware, verifier=LocalTokenVerifier(keys))

    @app.get("/secret")
    async def secret() -> JSONResponse:
        return JSONResponse({"ok": True})

    return app


def test_valid_api_key_returns_200() -> None:
    client = TestClient(_make_app(["my-api-key"]))
    response = client.get("/secret", headers={"X-Api-Key": "my-api-key"})
    assert response.status_code == 200


def test_missing_api_key_returns_401() -> None:
    client = TestClient(_make_app(["my-api-key"]))
    response = client.get("/secret")
    assert response.status_code == 401
    body = response.json()
    assert body["type"].endswith("unauthorized")


def test_invalid_api_key_returns_401() -> None:
    client = TestClient(_make_app(["my-api-key"]))
    response = client.get("/secret", headers={"X-Api-Key": "wrong-key"})
    assert response.status_code == 401


def test_multiple_allowed_keys() -> None:
    client = TestClient(_make_app(["key-a", "key-b"]))
    assert client.get("/secret", headers={"X-Api-Key": "key-a"}).status_code == 200
    assert client.get("/secret", headers={"X-Api-Key": "key-b"}).status_code == 200
    assert client.get("/secret", headers={"X-Api-Key": "key-c"}).status_code == 401


def test_exclude_paths_bypasses_auth() -> None:
    app = FastAPI()
    app.add_middleware(
        ApiKeyAuthMiddleware,
        verifier=LocalTokenVerifier(["key"]),
        exclude_paths=["/health"],
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


def test_verifier_raises_token_verification_exception_returns_401() -> None:
    """TokenVerificationException from verifier must return 401, not 500."""

    class ExplodingVerifier:
        def verify(self, token: str) -> bool:
            raise TokenVerificationException("simulated failure")

    app = FastAPI()
    app.add_middleware(
        ApiKeyAuthMiddleware,
        verifier=ExplodingVerifier(),  # type: ignore[arg-type]
    )

    @app.get("/secret")
    async def secret() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/secret", headers={"X-Api-Key": "any-key"})
    assert response.status_code == 401


def test_custom_header_name() -> None:
    app = FastAPI()
    app.add_middleware(
        ApiKeyAuthMiddleware,
        verifier=LocalTokenVerifier(["svc-token"]),
        header_name="X-Service-Token",
    )

    @app.get("/secret")
    async def secret() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/secret", headers={"X-Service-Token": "svc-token"}).status_code == 200
    assert client.get("/secret", headers={"X-Api-Key": "svc-token"}).status_code == 401


def test_custom_header_name_in_error_message() -> None:
    app = FastAPI()
    app.add_middleware(
        ApiKeyAuthMiddleware,
        verifier=LocalTokenVerifier(["tok"]),
        header_name="X-Internal-Key",
    )

    @app.get("/secret")
    async def secret() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/secret")
    assert response.status_code == 401
    assert "X-Internal-Key" in response.json().get("detail", "")


# ---------------------------------------------------------------------------
# include_paths tests
# ---------------------------------------------------------------------------
def test_include_paths_protects_matching_prefix() -> None:
    app = FastAPI()
    app.add_middleware(
        ApiKeyAuthMiddleware,
        verifier=LocalTokenVerifier(["key"]),
        include_paths=["/webhook"],
    )

    @app.get("/webhook/event")
    async def webhook_event() -> JSONResponse:
        return JSONResponse({"received": True})

    @app.get("/public/hello")
    async def public_hello() -> JSONResponse:
        return JSONResponse({"hello": True})

    client = TestClient(app)
    assert client.get("/webhook/event").status_code == 401
    assert client.get("/webhook/event", headers={"X-Api-Key": "key"}).status_code == 200
    assert client.get("/public/hello").status_code == 200


def test_include_paths_multiple_prefixes() -> None:
    app = FastAPI()
    app.add_middleware(
        ApiKeyAuthMiddleware,
        verifier=LocalTokenVerifier(["key"]),
        include_paths=["/webhook", "/internal"],
    )

    @app.get("/webhook/x")
    async def webhook_x() -> JSONResponse:
        return JSONResponse({"ok": True})

    @app.get("/internal/y")
    async def internal_y() -> JSONResponse:
        return JSONResponse({"ok": True})

    @app.get("/public/z")
    async def public_z() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    assert client.get("/webhook/x").status_code == 401
    assert client.get("/internal/y").status_code == 401
    assert client.get("/public/z").status_code == 200


def test_include_paths_takes_precedence_over_exclude_paths() -> None:
    """両方指定されたときは include_paths が優先される。"""
    app = FastAPI()
    app.add_middleware(
        ApiKeyAuthMiddleware,
        verifier=LocalTokenVerifier(["key"]),
        include_paths=["/webhook"],
        exclude_paths=["/webhook/open"],  # include_paths があるので無視される
    )

    @app.get("/webhook/open")
    async def webhook_open() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    assert client.get("/webhook/open").status_code == 401
