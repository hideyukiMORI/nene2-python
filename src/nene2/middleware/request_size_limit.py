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

    Use ``path_limits`` to set per-path limits that override the default::

        app.add_middleware(
            RequestSizeLimitMiddleware,
            max_bytes=1_048_576,  # default: 1 MiB
            path_limits={
                "/upload/file": 10_485_760,  # /upload/file: 10 MiB
                "/api/import": 5_242_880,  # /api/import: 5 MiB
            },
        )

    Use ``exclude_paths`` to bypass the size limit entirely::

        app.add_middleware(
            RequestSizeLimitMiddleware,
            max_bytes=1_048_576,
            exclude_paths=["/upload/multipart"],
        )
    """

    def __init__(
        self,
        app: object,
        *,
        max_bytes: int = _DEFAULT_MAX_BYTES,
        path_limits: dict[str, int] | None = None,
        exclude_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._max_bytes = max_bytes
        self._path_limits: dict[str, int] = path_limits or {}
        self._exclude_paths = set(exclude_paths or [])

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path in self._exclude_paths:
            return await call_next(request)

        effective_limit = self._path_limits.get(path, self._max_bytes)

        content_length = request.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > effective_limit:
                    return self._too_large(effective_limit)
            except ValueError:
                pass

        body = await request.body()
        if len(body) > effective_limit:
            return self._too_large(effective_limit)

        return await call_next(request)

    def _too_large(self, limit: int) -> Response:
        return problem_details_response(
            "payload-too-large",
            "Payload Too Large",
            413,
            _TOO_LARGE.format(limit=limit),
            extra={"max_bytes": limit},
        )
