"""GET /examples/protected — Bearer JWT parity with NENE2."""

import base64
import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient

from example.app import create_app
from nene2.config import AppSettings

_SECRET = "ft-evac-local-jwt-secret-min-32-chars!!"  # noqa: S105


def _bearer() -> str:
    now = int(time.time())
    header_b64 = (
        base64.urlsafe_b64encode(
            json.dumps({"typ": "JWT", "alg": "HS256"}).encode(),
        )
        .rstrip(b"=")
        .decode()
    )
    claims = {"sub": "user-42", "scope": "read:system", "iat": now, "exp": now + 3600}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    sig_b64 = (
        base64.urlsafe_b64encode(
            hmac.new(
                _SECRET.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256,
            ).digest(),
        )
        .rstrip(b"=")
        .decode()
    )
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def test_protected_requires_bearer() -> None:
    client = TestClient(create_app(AppSettings(throttle_enabled=False)))
    assert client.get("/examples/protected").status_code == 401


def test_protected_with_jwt() -> None:
    client = TestClient(create_app(AppSettings(throttle_enabled=False)))
    r = client.get("/examples/protected", headers={"Authorization": f"Bearer {_bearer()}"})
    assert r.status_code == 200
    body = r.json()
    assert "Welcome" in body["message"]
    assert body["claims"]["sub"] == "user-42"
