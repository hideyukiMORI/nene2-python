"""API Key authentication middleware.

Validates a configurable header (default: X-Api-Key) using a TokenVerifierProtocol.
Returns 401 Problem Details when key is absent or invalid.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response

from .exceptions import TokenVerificationException
from .interfaces import TokenVerifierProtocol

_DEFAULT_API_KEY_HEADER = "X-Api-Key"


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Require a valid API key header on matching requests.

    The header name defaults to ``X-Api-Key`` but can be customised.

    **Path filtering** — two complementary options (mutually exclusive):

    - ``include_paths``: only protect paths whose prefix matches one of these values.
      All other paths pass through without authentication.
      Ideal for protecting a specific sub-tree (e.g. ``["/webhook"]``).
    - ``exclude_paths``: protect every path **except** these exact paths.
      Ideal for skipping docs / health endpoints.

    When both are provided, ``include_paths`` takes precedence.

    Examples::

        # Protect only /webhook/* routes (prefix match)
        app.add_middleware(
            ApiKeyAuthMiddleware,
            verifier=LocalTokenVerifier(api_keys),
            include_paths=["/webhook"],
        )

        # Protect everything except docs/health (exact match)
        app.add_middleware(
            ApiKeyAuthMiddleware,
            verifier=LocalTokenVerifier(api_keys),
            header_name="X-Service-Token",
            exclude_paths=["/docs", "/openapi.json", "/redoc", "/health"],
        )
    """

    def __init__(
        self,
        app: object,
        *,
        verifier: TokenVerifierProtocol,
        header_name: str = _DEFAULT_API_KEY_HEADER,
        exclude_paths: list[str] | None = None,
        include_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._verifier = verifier
        self._header_name = header_name
        self._exclude_paths = set(exclude_paths or [])
        self._include_paths = list(include_paths or [])

    def _should_authenticate(self, path: str) -> bool:
        if self._include_paths:
            return any(path.startswith(prefix) for prefix in self._include_paths)
        return path not in self._exclude_paths

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._should_authenticate(request.url.path):
            return await call_next(request)
        api_key = request.headers.get(self._header_name, "")
        try:
            verified = bool(api_key) and self._verifier.verify(api_key)
        except TokenVerificationException:
            verified = False
        if not verified:
            return problem_details_response(
                "unauthorized",
                "Unauthorized",
                401,
                f"A valid {self._header_name} header is required.",
            )
        return await call_next(request)
