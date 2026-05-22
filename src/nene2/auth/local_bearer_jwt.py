"""HS256 JWT verifier compatible with NENE2 LocalBearerTokenVerifier (dev/FT only)."""

import base64
import hashlib
import hmac
import json
import time

from .exceptions import TokenVerificationException


def _b64url_decode(segment: str) -> bytes:
    padding = (4 - len(segment) % 4) % 4
    return base64.urlsafe_b64decode(segment + "=" * padding)


class LocalBearerJwtVerifier:
    """Verify NENE2-style HS256 JWT bearer tokens (three dot-separated segments)."""

    def __init__(self, secret: str) -> None:
        if len(secret) < 32:
            msg = "JWT secret must be at least 32 characters for local bearer verification."
            raise ValueError(msg)
        self._secret = secret.encode("utf-8")

    def decode_claims(self, token: str) -> dict[str, object]:
        """Return claims when valid; raises TokenVerificationException otherwise."""
        parts = token.split(".")
        if len(parts) != 3:
            raise TokenVerificationException("Token format is invalid: expected three segments.")
        header_b64, payload_b64, sig_b64 = parts
        header = json.loads(_b64url_decode(header_b64))
        if header.get("alg") != "HS256":
            raise TokenVerificationException("Token algorithm must be HS256.")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = base64.urlsafe_b64encode(
            hmac.new(self._secret, signing_input, hashlib.sha256).digest(),
        ).rstrip(b"=").decode()
        if not hmac.compare_digest(expected_sig, sig_b64):
            raise TokenVerificationException("Token signature is invalid.")
        claims: dict[str, object] = json.loads(_b64url_decode(payload_b64))
        now = int(time.time())
        nbf = claims.get("nbf")
        if isinstance(nbf, int) and nbf > now:
            raise TokenVerificationException("Token is not yet valid.")
        exp = claims.get("exp")
        if isinstance(exp, int) and exp < now:
            raise TokenVerificationException("Token has expired.")
        return claims

    def verify(self, token: str) -> bool:
        try:
            self.decode_claims(token)
        except TokenVerificationException:
            return False
        return True
