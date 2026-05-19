"""Local token verifier — compares against a fixed set of allowed tokens.

For development and testing only. In production, implement TokenVerifierProtocol
against your actual auth backend (database, external IdP, JWT, etc.).
"""

import secrets


class LocalTokenVerifier:
    """Verify tokens against a fixed allowlist using constant-time comparison."""

    def __init__(self, allowed_tokens: list[str]) -> None:
        self._allowed = allowed_tokens

    def verify(self, token: str) -> bool:
        return any(secrets.compare_digest(token, allowed) for allowed in self._allowed)
