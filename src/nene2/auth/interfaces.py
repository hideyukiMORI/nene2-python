"""Authentication interfaces."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenVerifierProtocol(Protocol):
    """Verify an authentication token."""

    def verify(self, token: str) -> bool: ...
