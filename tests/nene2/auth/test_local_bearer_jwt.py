"""LocalBearerJwtVerifier — NENE2 HS256 JWT parity."""

import base64
import hashlib
import hmac
import json
import time

import pytest

from nene2.auth import LocalBearerJwtVerifier
from nene2.auth.exceptions import TokenVerificationException

_SECRET = "ft-evac-local-jwt-secret-min-32-chars!!"  # noqa: S105


def _issue(secret: str, claims: dict[str, object]) -> str:
    header_b64 = (
        base64.urlsafe_b64encode(
            json.dumps({"typ": "JWT", "alg": "HS256"}).encode(),
        )
        .rstrip(b"=")
        .decode()
    )
    payload_b64 = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    sig_b64 = (
        base64.urlsafe_b64encode(
            hmac.new(
                secret.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256,
            ).digest(),
        )
        .rstrip(b"=")
        .decode()
    )
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def test_verify_and_decode_ok() -> None:
    now = int(time.time())
    claims = {"sub": "user-42", "scope": "read:system", "iat": now, "exp": now + 3600}
    token = _issue(_SECRET, claims)
    verifier = LocalBearerJwtVerifier(_SECRET)
    assert verifier.verify(token) is True
    claims = verifier.decode_claims(token)
    assert claims["sub"] == "user-42"


def test_rejects_expired() -> None:
    now = int(time.time())
    token = _issue(_SECRET, {"sub": "x", "exp": now - 10})
    verifier = LocalBearerJwtVerifier(_SECRET)
    with pytest.raises(TokenVerificationException):
        verifier.decode_claims(token)


def test_secret_too_short() -> None:
    with pytest.raises(ValueError):
        LocalBearerJwtVerifier("short")
