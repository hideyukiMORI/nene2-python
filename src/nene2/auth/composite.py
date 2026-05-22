"""CompositeAuthMiddleware — path-prefix-based auth strategy routing."""

from collections.abc import Callable
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response

from .exceptions import TokenVerificationException
from .interfaces import TokenVerifierProtocol

type AuthCheck = Callable[[Request], Response | None]

_WWW_AUTH_BEARER = 'Bearer realm="api"'


@dataclass(frozen=True, slots=True)
class CompositeAuthRule:
    """Single routing rule: path prefix → authentication check.

    Use :func:`bearer_check` or :func:`api_key_check` to build the ``check`` callable.
    """

    path_prefix: str
    check: AuthCheck


def bearer_check(verifier: TokenVerifierProtocol) -> AuthCheck:
    """Build an AuthCheck that validates ``Authorization: Bearer <token>``."""

    def _check(request: Request) -> Response | None:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            resp = problem_details_response(
                "unauthorized",
                "Unauthorized",
                401,
                "A valid Bearer token is required.",
            )
            resp.headers["WWW-Authenticate"] = _WWW_AUTH_BEARER
            return resp
        token = auth[len("Bearer ") :]
        try:
            verified = verifier.verify(token)
        except TokenVerificationException:
            verified = False
        if not verified:
            resp = problem_details_response(
                "unauthorized",
                "Unauthorized",
                401,
                "The provided token is invalid or expired.",
            )
            resp.headers["WWW-Authenticate"] = _WWW_AUTH_BEARER
            return resp
        return None

    return _check


def api_key_check(
    verifier: TokenVerifierProtocol,
    header_name: str = "X-Api-Key",
) -> AuthCheck:
    """Build an AuthCheck that validates a configurable API key header."""

    def _check(request: Request) -> Response | None:
        api_key = request.headers.get(header_name, "")
        try:
            verified = bool(api_key) and verifier.verify(api_key)
        except TokenVerificationException:
            verified = False
        if not verified:
            return problem_details_response(
                "unauthorized",
                "Unauthorized",
                401,
                f"A valid {header_name} header is required.",
            )
        return None

    return _check


class CompositeAuthMiddleware(BaseHTTPMiddleware):
    """Apply different auth strategies to different path prefixes.

    Rules are evaluated in order; the first matching prefix wins.
    If no rule matches, the request passes through unauthenticated.

    Example::

        from nene2.auth import (
            CompositeAuthMiddleware,
            CompositeAuthRule,
            api_key_check,
            bearer_check,
        )

        app.add_middleware(
            CompositeAuthMiddleware,
            rules=[
                CompositeAuthRule("/webhook", api_key_check(webhook_verifier, "X-Webhook-Key")),
                CompositeAuthRule("/api", bearer_check(token_verifier)),
            ],
        )
    """

    def __init__(
        self,
        app: object,
        *,
        rules: list[CompositeAuthRule],
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._rules = rules

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        for rule in self._rules:
            if path.startswith(rule.path_prefix):
                rejection = rule.check(request)
                if rejection is not None:
                    return rejection
                break
        return await call_next(request)
