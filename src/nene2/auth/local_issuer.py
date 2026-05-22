"""LocalTokenIssuer / LocalTokenIssuerVerifier — HMAC-signed dev tokens.

For development and testing only.  In production use a proper JWT library
(e.g. PyJWT) backed by your key management system.
"""

import base64
import hmac
import json


class LocalTokenIssuer:
    """Issue self-contained HMAC-SHA256-signed tokens for development/testing.

    Generates tokens as ``{b64url_claims}.{hmac_hex}`` so claims are
    readable without a round-trip to a token store.

    Pair with :class:`LocalTokenIssuerVerifier` using the same *signing_key*
    to create a complete dev auth setup::

        key = "dev-secret"
        issuer = LocalTokenIssuer(key)
        verifier = LocalTokenIssuerVerifier(key)

        token = issuer.issue({"sub": "user-1", "role": "admin"})
        verifier.verify(token)  # → True
        verifier.decode(token)  # → {"sub": "user-1", "role": "admin"}
    """

    def __init__(self, signing_key: str) -> None:
        self._key = signing_key.encode("utf-8")

    def issue(self, claims: dict[str, object]) -> str:
        payload = json.dumps(claims, sort_keys=True, ensure_ascii=False)
        b64 = base64.urlsafe_b64encode(payload.encode()).rstrip(b"=").decode()
        sig = hmac.new(self._key, b64.encode(), digestmod="sha256").hexdigest()
        return f"{b64}.{sig}"


class LocalTokenIssuerVerifier:
    """Verify and decode tokens issued by :class:`LocalTokenIssuer`.

    Implements :class:`~nene2.auth.TokenVerifierProtocol`.
    """

    def __init__(self, signing_key: str) -> None:
        self._key = signing_key.encode("utf-8")

    def verify(self, token: str) -> bool:
        """Return True if the token has a valid HMAC signature."""
        try:
            b64, sig = token.rsplit(".", 1)
        except ValueError:
            return False
        expected = hmac.new(self._key, b64.encode(), digestmod="sha256").hexdigest()
        return hmac.compare_digest(sig, expected)

    def decode(self, token: str) -> dict[str, object] | None:
        """Return the decoded claims if the token is valid, else None."""
        try:
            b64, sig = token.rsplit(".", 1)
        except ValueError:
            return None
        expected = hmac.new(self._key, b64.encode(), digestmod="sha256").hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        padding = (4 - len(b64) % 4) % 4
        decoded = base64.urlsafe_b64decode(b64 + "=" * padding)
        result: dict[str, object] = json.loads(decoded)
        return result
