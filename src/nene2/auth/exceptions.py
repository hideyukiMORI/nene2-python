"""Authentication exceptions."""


class TokenVerificationException(Exception):
    """Raised by TokenVerifierProtocol implementations when a token is invalid.

    BearerTokenMiddleware maps this to a 401 Problem Details response.
    """
