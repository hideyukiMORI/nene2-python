"""Request body size limit middleware.

Rejects requests whose Content-Length exceeds the configured maximum.
Protects against memory exhaustion from oversized payloads.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response

_DEFAULT_MAX_BYTES = 1_048_576  # 1 MiB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds max_bytes."""

    def __init__(self, app: object, *, max_bytes: int = _DEFAULT_MAX_BYTES) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("Content-Length")
        if content_length is not None and int(content_length) > self._max_bytes:
            return problem_details_response(
                "payload-too-large",
                "Payload Too Large",
                413,
                f"Request body must not exceed {self._max_bytes} bytes.",
            )
        return await call_next(request)
