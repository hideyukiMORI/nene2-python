"""Bearer token authentication middleware.

Validates Authorization: Bearer <token> header.
Returns 401 Problem Details when token is absent or invalid.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response

from .interfaces import TokenVerifierProtocol

_WWW_AUTH = 'Bearer realm="api"'


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Require a valid Bearer token on every request."""

    def __init__(self, app: object, *, verifier: TokenVerifierProtocol) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._verifier = verifier

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            response = problem_details_response(
                "unauthorized",
                "Unauthorized",
                401,
                "A valid Bearer token is required.",
            )
            response.headers["WWW-Authenticate"] = _WWW_AUTH
            return response
        token = auth[len("Bearer "):]
        if not self._verifier.verify(token):
            response = problem_details_response(
                "unauthorized",
                "Unauthorized",
                401,
                "The provided token is invalid or expired.",
            )
            response.headers["WWW-Authenticate"] = _WWW_AUTH
            return response
        return await call_next(request)
