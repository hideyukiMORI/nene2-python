"""Authentication interfaces."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenVerifierProtocol(Protocol):
    """Verify an authentication token.

    Implementations may raise TokenVerificationException instead of returning False.
    """

    def verify(self, token: str) -> bool: ...


@runtime_checkable
class TokenIssuerProtocol(Protocol):
    """Issue a signed bearer token from the given claims.

    Production implementations wrap a JWT library (e.g. PyJWT).
    """

    def issue(self, claims: dict[str, object]) -> str: ...
