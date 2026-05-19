"""API Key authentication middleware.

Validates X-Api-Key header using a TokenVerifierProtocol.
Returns 401 Problem Details when key is absent or invalid.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response

from .interfaces import TokenVerifierProtocol

_API_KEY_HEADER = "X-Api-Key"


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Require a valid X-Api-Key header on every request."""

    def __init__(self, app: object, *, verifier: TokenVerifierProtocol) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._verifier = verifier

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        api_key = request.headers.get(_API_KEY_HEADER, "")
        if not api_key or not self._verifier.verify(api_key):
            return problem_details_response(
                "unauthorized",
                "Unauthorized",
                401,
                "A valid X-Api-Key header is required.",
            )
        return await call_next(request)
