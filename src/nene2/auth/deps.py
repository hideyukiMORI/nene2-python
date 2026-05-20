"""FastAPI Depends utilities for authentication.

Provides ``make_require_auth`` to wire :class:`TokenVerifierProtocol` into
FastAPI's dependency injection system without boilerplate.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .interfaces import TokenVerifierProtocol

_security = HTTPBearer(auto_error=False)


def make_require_auth(verifier: TokenVerifierProtocol) -> Callable[..., str]:
    """Return a FastAPI Depends-compatible callable that enforces token authentication.

    Usage::

        from nene2.auth import LocalTokenVerifier, make_require_auth

        verifier = LocalTokenVerifier.from_env("BEARER_TOKENS")
        require_auth = make_require_auth(verifier)


        @app.post("/items")
        def create_item(
            body: ItemBody,
            token: Annotated[str, Depends(require_auth)],
        ) -> JSONResponse: ...

    Args:
        verifier: A :class:`TokenVerifierProtocol` implementation to validate tokens.

    Returns:
        A dependency function that returns the raw token string when authenticated,
        or raises ``HTTP 401`` when the token is absent or invalid.
    """

    def _get_token(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)],
    ) -> str:
        if credentials is None or not verifier.verify(credentials.credentials):
            raise HTTPException(status_code=401, detail="Invalid or missing token")
        return credentials.credentials

    return _get_token
