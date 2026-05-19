"""Bearer token authentication middleware.

Validates Authorization: Bearer <token> header.
Returns 401 Problem Details when token is absent or invalid.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response

from .exceptions import TokenVerificationException
from .interfaces import TokenVerifierProtocol

_WWW_AUTH = 'Bearer realm="api"'


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Require a valid Bearer token on every request.

    Use ``exclude_paths`` to skip authentication for specific paths such as
    health-check endpoints or API documentation::

        app.add_middleware(
            BearerTokenMiddleware,
            verifier=LocalTokenVerifier(tokens),
            exclude_paths=["/docs", "/openapi.json", "/redoc", "/health"],
        )
    """

    def __init__(
        self,
        app: object,
        *,
        verifier: TokenVerifierProtocol,
        exclude_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._verifier = verifier
        self._exclude_paths = set(exclude_paths or [])

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._exclude_paths:
            return await call_next(request)
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
        token = auth[len("Bearer ") :]
        try:
            verified = self._verifier.verify(token)
        except TokenVerificationException:
            verified = False
        if not verified:
            response = problem_details_response(
                "unauthorized",
                "Unauthorized",
                401,
                "The provided token is invalid or expired.",
            )
            response.headers["WWW-Authenticate"] = _WWW_AUTH
            return response
        return await call_next(request)
