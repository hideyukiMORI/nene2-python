"""NENE2 authentication layer."""

from .api_key import ApiKeyAuthMiddleware
from .bearer_token import BearerTokenMiddleware
from .composite import (
    AuthCheck,
    CompositeAuthMiddleware,
    CompositeAuthRule,
    api_key_check,
    bearer_check,
)
from .deps import make_require_auth
from .exceptions import TokenVerificationException
from .interfaces import TokenIssuerProtocol, TokenVerifierProtocol
from .local_issuer import LocalTokenIssuer, LocalTokenIssuerVerifier
from .local_verifier import LocalTokenVerifier

__all__ = [
    "ApiKeyAuthMiddleware",
    "AuthCheck",
    "BearerTokenMiddleware",
    "CompositeAuthMiddleware",
    "CompositeAuthRule",
    "LocalTokenIssuer",
    "LocalTokenIssuerVerifier",
    "LocalTokenVerifier",
    "TokenIssuerProtocol",
    "TokenVerificationException",
    "TokenVerifierProtocol",
    "api_key_check",
    "bearer_check",
    "make_require_auth",
]
