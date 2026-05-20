"""Local token verifier — compares against a fixed set of allowed tokens.

For development and testing only. In production, implement TokenVerifierProtocol
against your actual auth backend (database, external IdP, JWT, etc.).
"""

import os
import secrets


class LocalTokenVerifier:
    """Verify tokens against a fixed allowlist using constant-time comparison."""

    def __init__(self, allowed_tokens: list[str] | set[str] | frozenset[str]) -> None:
        self._allowed: frozenset[str] = frozenset(allowed_tokens)

    @classmethod
    def from_env(cls, env_var: str, *, separator: str = ",") -> "LocalTokenVerifier":
        """Create a verifier from a separator-delimited environment variable.

        Example .env::

            BEARER_TOKENS = token - a, token - b, token - c

        Usage::

            verifier = LocalTokenVerifier.from_env("BEARER_TOKENS")

        An unset or empty variable results in an empty allowlist (all requests denied).
        """
        raw = os.getenv(env_var, "")
        tokens = [t.strip() for t in raw.split(separator) if t.strip()]
        return cls(tokens)

    def verify(self, token: str) -> bool:
        return any(secrets.compare_digest(token, allowed) for allowed in self._allowed)
