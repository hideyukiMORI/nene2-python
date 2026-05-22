"""System route parity with NENE2 OpenAPI (GET /, /machine/health)."""

from fastapi.testclient import TestClient

from example.app import create_app
from nene2.config import AppSettings

_MACHINE_KEY = "ft-evac-local-machine-api-key-32ch!!"


def test_framework_smoke_root() -> None:
    client = TestClient(create_app(AppSettings(throttle_enabled=False)))
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "NENE2"
    assert body["status"] == "ok"
    assert "description" in body


def test_machine_health_requires_api_key() -> None:
    client = TestClient(create_app(AppSettings(throttle_enabled=False)))
    assert client.get("/machine/health").status_code == 401


def test_machine_health_with_api_key() -> None:
    client = TestClient(create_app(AppSettings(throttle_enabled=False)))
    r = client.get("/machine/health", headers={"X-NENE2-API-Key": _MACHINE_KEY})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "NENE2"
    assert body["credential_type"] == "api_key"
