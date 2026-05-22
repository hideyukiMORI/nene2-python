"""CompositeAuthMiddleware / bearer_check / api_key_check のテスト。"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.auth import (
    CompositeAuthMiddleware,
    CompositeAuthRule,
    LocalTokenVerifier,
    api_key_check,
    bearer_check,
)


def _make_app(rules: list[CompositeAuthRule]) -> FastAPI:
    app = FastAPI()
    app.add_middleware(CompositeAuthMiddleware, rules=rules)

    @app.get("/api/notes")
    async def notes() -> JSONResponse:
        return JSONResponse({"resource": "api"})

    @app.get("/webhook/event")
    async def webhook() -> JSONResponse:
        return JSONResponse({"resource": "webhook"})

    @app.get("/public/status")
    async def public() -> JSONResponse:
        return JSONResponse({"resource": "public"})

    return app


# ---------------------------------------------------------------------------
# bearer_check
# ---------------------------------------------------------------------------


def test_bearer_check_valid_token_passes() -> None:
    rules = [CompositeAuthRule("/api", bearer_check(LocalTokenVerifier(["tok"])))]
    client = TestClient(_make_app(rules))
    response = client.get("/api/notes", headers={"Authorization": "Bearer tok"})
    assert response.status_code == 200


def test_bearer_check_missing_header_returns_401() -> None:
    rules = [CompositeAuthRule("/api", bearer_check(LocalTokenVerifier(["tok"])))]
    client = TestClient(_make_app(rules))
    response = client.get("/api/notes")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


def test_bearer_check_invalid_token_returns_401() -> None:
    rules = [CompositeAuthRule("/api", bearer_check(LocalTokenVerifier(["tok"])))]
    client = TestClient(_make_app(rules))
    response = client.get("/api/notes", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# api_key_check
# ---------------------------------------------------------------------------


def test_api_key_check_valid_key_passes() -> None:
    check = api_key_check(LocalTokenVerifier(["secret"]), "X-Webhook-Key")
    rules = [CompositeAuthRule("/webhook", check)]
    client = TestClient(_make_app(rules))
    response = client.get("/webhook/event", headers={"X-Webhook-Key": "secret"})
    assert response.status_code == 200


def test_api_key_check_missing_key_returns_401() -> None:
    check = api_key_check(LocalTokenVerifier(["secret"]), "X-Webhook-Key")
    rules = [CompositeAuthRule("/webhook", check)]
    client = TestClient(_make_app(rules))
    response = client.get("/webhook/event")
    assert response.status_code == 401


def test_api_key_check_default_header_name() -> None:
    rules = [CompositeAuthRule("/webhook", api_key_check(LocalTokenVerifier(["key"])))]
    client = TestClient(_make_app(rules))
    response = client.get("/webhook/event", headers={"X-Api-Key": "key"})
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# CompositeAuthMiddleware routing
# ---------------------------------------------------------------------------


def test_unmatched_path_passes_through() -> None:
    rules = [CompositeAuthRule("/api", bearer_check(LocalTokenVerifier(["tok"])))]
    client = TestClient(_make_app(rules))
    response = client.get("/public/status")
    assert response.status_code == 200


def test_first_matching_rule_wins() -> None:
    rules = [
        CompositeAuthRule("/api", bearer_check(LocalTokenVerifier(["bearer-tok"]))),
        CompositeAuthRule("/api", api_key_check(LocalTokenVerifier(["api-key"]))),
    ]
    client = TestClient(_make_app(rules))
    response = client.get("/api/notes", headers={"Authorization": "Bearer bearer-tok"})
    assert response.status_code == 200
    response2 = client.get("/api/notes", headers={"X-Api-Key": "api-key"})
    assert response2.status_code == 401


def test_different_paths_use_different_auth() -> None:
    wh_check = api_key_check(LocalTokenVerifier(["wh-key"]), "X-Webhook-Key")
    rules = [
        CompositeAuthRule("/api", bearer_check(LocalTokenVerifier(["bearer-tok"]))),
        CompositeAuthRule("/webhook", wh_check),
    ]
    client = TestClient(_make_app(rules))
    api_ok = client.get("/api/notes", headers={"Authorization": "Bearer bearer-tok"})
    api_fail = client.get("/api/notes", headers={"X-Webhook-Key": "wh-key"})
    wh_ok = client.get("/webhook/event", headers={"X-Webhook-Key": "wh-key"})
    wh_fail = client.get("/webhook/event", headers={"Authorization": "Bearer bearer-tok"})
    assert api_ok.status_code == 200
    assert api_fail.status_code == 401
    assert wh_ok.status_code == 200
    assert wh_fail.status_code == 401


def test_empty_rules_passes_all() -> None:
    client = TestClient(_make_app([]))
    assert client.get("/api/notes").status_code == 200
    assert client.get("/webhook/event").status_code == 200
