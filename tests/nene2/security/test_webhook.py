"""Tests for nene2.security.webhook."""

import hashlib
import hmac

import pytest

from nene2.security import verify_hmac_signature


def _make_sig(body: bytes, secret: str, prefix: str = "") -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return prefix + digest


def test_verify_returns_true_when_signature_matches() -> None:
    body = b'{"action": "opened"}'
    sig = _make_sig(body, "mysecret", prefix="sha256=")
    assert verify_hmac_signature(body, "mysecret", sig, prefix="sha256=") is True


def test_verify_returns_false_for_wrong_secret() -> None:
    body = b'{"action": "opened"}'
    sig = _make_sig(body, "correct-secret", prefix="sha256=")
    assert verify_hmac_signature(body, "wrong-secret", sig, prefix="sha256=") is False


def test_verify_returns_false_for_tampered_body() -> None:
    original = b'{"amount": 100}'
    tampered = b'{"amount": 999}'
    sig = _make_sig(original, "secret", prefix="sha256=")
    assert verify_hmac_signature(tampered, "secret", sig, prefix="sha256=") is False


def test_verify_without_prefix() -> None:
    body = b"raw data"
    sig = _make_sig(body, "secret")
    assert verify_hmac_signature(body, "secret", sig) is True


def test_verify_returns_false_for_invalid_hex_signature() -> None:
    body = b"data"
    assert verify_hmac_signature(body, "secret", "sha256=notahexstring", prefix="sha256=") is False


def test_verify_empty_body() -> None:
    body = b""
    sig = _make_sig(body, "secret", prefix="sha256=")
    assert verify_hmac_signature(body, "secret", sig, prefix="sha256=") is True


def test_verify_unicode_secret() -> None:
    body = b'{"event": "test"}'
    secret = "シークレット"  # noqa: S105
    sig = _make_sig(body, secret, prefix="sha256=")
    assert verify_hmac_signature(body, secret, sig, prefix="sha256=") is True


@pytest.mark.parametrize("body", [b"a", b"hello world", b'{"key": "value"}'])
def test_verify_deterministic(body: bytes) -> None:
    sig = _make_sig(body, "key", prefix="sha256=")
    assert verify_hmac_signature(body, "key", sig, prefix="sha256=") is True
