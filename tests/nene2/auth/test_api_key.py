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
