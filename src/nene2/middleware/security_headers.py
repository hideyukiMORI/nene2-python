"""Security headers middleware.

Adds defensive HTTP headers to every response.
CSP is skipped for OpenAPI documentation paths (/docs, /redoc, /openapi.json)
because Swagger UI loads assets from CDN which would be blocked by default-src 'self'.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_DEFAULT_CSP = "default-src 'self'"
_DEFAULT_PERMISSIONS_POLICY = "geolocation=(), microphone=()"

_STATIC_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}

_DEFAULT_NO_CSP_PATHS: frozenset[str] = frozenset({"/docs", "/redoc", "/openapi.json"})


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach security headers to every HTTP response.

    Content-Security-Policy is omitted for OpenAPI documentation paths so that
    Swagger UI and ReDoc (which load assets from CDN) continue to work in development.

    Args:
        csp: Custom Content-Security-Policy header value.
            Defaults to ``"default-src 'self'"`` when not specified.
        permissions_policy: Custom Permissions-Policy header value.
            Defaults to ``"geolocation=(), microphone=()"`` when not specified.
        hsts: Strict-Transport-Security header value (e.g.
            ``"max-age=31536000; includeSubDomains"``). Not set by default.
            Enable only in production environments serving HTTPS.
        extra_no_csp_paths: Additional paths to skip the CSP header for.
            Useful when FastAPI is configured with custom ``docs_url`` / ``redoc_url``.
            The built-in paths ``/docs``, ``/redoc``, and ``/openapi.json`` are always included.
    """

    def __init__(
        self,
        app: object,
        csp: str | None = None,
        permissions_policy: str | None = None,
        hsts: str | None = None,
        extra_no_csp_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._csp = csp if csp is not None else _DEFAULT_CSP
        self._permissions_policy = (
            permissions_policy if permissions_policy is not None else _DEFAULT_PERMISSIONS_POLICY
        )
        self._hsts = hsts
        self._no_csp_paths = _DEFAULT_NO_CSP_PATHS | frozenset(extra_no_csp_paths or [])

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for header, value in _STATIC_HEADERS.items():
            response.headers[header] = value
        response.headers["Permissions-Policy"] = self._permissions_policy
        if self._hsts:
            response.headers["Strict-Transport-Security"] = self._hsts
        if request.url.path not in self._no_csp_paths:
            response.headers["Content-Security-Policy"] = self._csp
        return response
