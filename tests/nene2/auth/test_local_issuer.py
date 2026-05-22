"""LocalTokenIssuer / LocalTokenIssuerVerifier のテスト。"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.auth import (
    BearerTokenMiddleware,
    LocalTokenIssuer,
    LocalTokenIssuerVerifier,
    TokenIssuerProtocol,
    TokenVerifierProtocol,
)

_KEY = "test-signing-key"


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_local_token_issuer_satisfies_protocol() -> None:
    assert isinstance(LocalTokenIssuer(_KEY), TokenIssuerProtocol)


def test_local_token_issuer_verifier_satisfies_verifier_protocol() -> None:
    assert isinstance(LocalTokenIssuerVerifier(_KEY), TokenVerifierProtocol)


# ---------------------------------------------------------------------------
# issue / verify round-trip
# ---------------------------------------------------------------------------


def test_issued_token_verifies_successfully() -> None:
    issuer = LocalTokenIssuer(_KEY)
    verifier = LocalTokenIssuerVerifier(_KEY)
    token = issuer.issue({"sub": "user-1"})
    assert verifier.verify(token) is True


def test_token_from_different_key_fails_verification() -> None:
    issuer = LocalTokenIssuer("key-a")
    verifier = LocalTokenIssuerVerifier("key-b")
    assert verifier.verify(issuer.issue({"sub": "x"})) is False


def test_tampered_token_fails_verification() -> None:
    issuer = LocalTokenIssuer(_KEY)
    verifier = LocalTokenIssuerVerifier(_KEY)
    token = issuer.issue({"sub": "user-1"})
    tampered = token[:-4] + "zzzz"
    assert verifier.verify(tampered) is False


def test_malformed_token_fails_verification() -> None:
    verifier = LocalTokenIssuerVerifier(_KEY)
    assert verifier.verify("no-dot-here") is False
    assert verifier.verify("") is False


# ---------------------------------------------------------------------------
# decode
# ---------------------------------------------------------------------------


def test_decode_returns_original_claims() -> None:
    issuer = LocalTokenIssuer(_KEY)
    verifier = LocalTokenIssuerVerifier(_KEY)
    claims: dict[str, object] = {"sub": "user-1", "role": "admin", "n": 42}
    token = issuer.issue(claims)
    decoded = verifier.decode(token)
    assert decoded == claims


def test_decode_returns_none_for_invalid_token() -> None:
    verifier = LocalTokenIssuerVerifier(_KEY)
    assert verifier.decode("invalid") is None
    assert verifier.decode("part1.badsig") is None


def test_different_claims_produce_different_tokens() -> None:
    issuer = LocalTokenIssuer(_KEY)
    t1 = issuer.issue({"sub": "a"})
    t2 = issuer.issue({"sub": "b"})
    assert t1 != t2


def test_same_claims_produce_same_token() -> None:
    issuer = LocalTokenIssuer(_KEY)
    claims: dict[str, object] = {"sub": "user-1", "role": "viewer"}
    assert issuer.issue(claims) == issuer.issue(claims)


# ---------------------------------------------------------------------------
# Integration with BearerTokenMiddleware
# ---------------------------------------------------------------------------


def test_integration_with_bearer_middleware() -> None:
    key = "integration-key"
    issuer = LocalTokenIssuer(key)
    verifier = LocalTokenIssuerVerifier(key)

    app = FastAPI()
    app.add_middleware(BearerTokenMiddleware, verifier=verifier)

    @app.get("/secure")
    async def secure() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    token = issuer.issue({"sub": "test-user"})
    assert client.get("/secure", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.get("/secure", headers={"Authorization": "Bearer bad"}).status_code == 401
