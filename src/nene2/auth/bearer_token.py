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
    """Require a valid Bearer token on matching requests.

    **Path filtering** — two complementary options (mutually exclusive):

    - ``include_paths``: only protect paths whose prefix matches one of these values.
      All other paths pass through without authentication.
      Ideal for protecting a specific sub-tree (e.g. ``["/admin"]``).
    - ``exclude_paths``: protect every path **except** these exact paths.
      Ideal for skipping docs / health endpoints.

    When both are provided, ``include_paths`` takes precedence.

    Examples::

        # Protect only /admin/* routes (prefix match)
        app.add_middleware(
            BearerTokenMiddleware,
            verifier=LocalTokenVerifier(tokens),
            include_paths=["/admin"],
        )

        # Protect everything except docs/health (exact match)
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
        include_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._verifier = verifier
        self._exclude_paths = set(exclude_paths or [])
        self._include_paths = list(include_paths or [])

    def _should_authenticate(self, path: str) -> bool:
        if self._include_paths:
            return any(path.startswith(prefix) for prefix in self._include_paths)
        return path not in self._exclude_paths

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._should_authenticate(request.url.path):
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
        decode_claims = getattr(self._verifier, "decode_claims", None)
        if callable(decode_claims):
            try:
                request.state.nene2_auth_claims = decode_claims(token)
            except TokenVerificationException:
                response = problem_details_response(
                    "unauthorized",
                    "Unauthorized",
                    401,
                    "The provided token is invalid or expired.",
                )
                response.headers["WWW-Authenticate"] = _WWW_AUTH
                return response
        request.state.nene2_auth_credential_type = "bearer"
        return await call_next(request)
