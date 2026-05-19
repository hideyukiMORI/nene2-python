"""Security headers middleware.

Adds defensive HTTP headers to every response.
CSP is skipped for OpenAPI documentation paths (/docs, /redoc, /openapi.json)
because Swagger UI loads assets from CDN which would be blocked by default-src 'self'.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'",
    "Permissions-Policy": "geolocation=(), microphone=()",
}

_OPENAPI_PATHS: frozenset[str] = frozenset({"/docs", "/redoc", "/openapi.json"})


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach security headers to every HTTP response.

    Content-Security-Policy is omitted for OpenAPI documentation paths so that
    Swagger UI and ReDoc (which load assets from CDN) continue to work in development.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        is_openapi_path = request.url.path in _OPENAPI_PATHS
        for header, value in _HEADERS.items():
            if is_openapi_path and header == "Content-Security-Policy":
                continue
            response.headers[header] = value
        return response
