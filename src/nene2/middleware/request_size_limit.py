"""Request body size limit middleware.

Rejects requests whose body exceeds the configured maximum.
Protects against memory exhaustion from oversized payloads, including
chunked-transfer requests that omit the Content-Length header.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response

_DEFAULT_MAX_BYTES = 1_048_576  # 1 MiB

_TOO_LARGE = "Request body must not exceed {limit} bytes."


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose body exceeds max_bytes.

    Checks the Content-Length header first for a fast pre-flight reject,
    then reads the actual body to catch chunked-transfer requests that
    omit Content-Length entirely.
    """

    def __init__(self, app: object, *, max_bytes: int = _DEFAULT_MAX_BYTES) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > self._max_bytes:
                    return self._too_large()
            except ValueError:
                pass

        body = await request.body()
        if len(body) > self._max_bytes:
            return self._too_large()

        return await call_next(request)

    def _too_large(self) -> Response:
        return problem_details_response(
            "payload-too-large",
            "Payload Too Large",
            413,
            _TOO_LARGE.format(limit=self._max_bytes),
        )
