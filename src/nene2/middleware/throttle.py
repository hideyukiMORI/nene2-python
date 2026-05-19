"""Fixed-window rate limiting middleware.

Tracks request counts per client IP in an in-memory dict.
Exceeding the limit returns 429 with a Retry-After header.

.. warning::
    ``X-Forwarded-For`` is trusted as-is when present.  In environments
    **without** a trusted reverse proxy this header can be spoofed by clients,
    allowing them to bypass the rate limit.  Deploy behind a proxy that strips
    or overwrites the header (e.g. nginx ``proxy_set_header X-Forwarded-For
    $remote_addr``) before enabling this middleware in production.
"""

import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response

_DEFAULT_LIMIT = 60
_DEFAULT_WINDOW = 60  # seconds


class ThrottleMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limiter keyed by client IP."""

    def __init__(
        self,
        app: object,
        *,
        limit: int = _DEFAULT_LIMIT,
        window: int = _DEFAULT_WINDOW,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._limit = limit
        self._window = window
        self._counts: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_allowed(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            count, window_start = self._counts.get(key, (0, now))
            if now - window_start >= self._window:
                count, window_start = 0, now
            count += 1
            self._counts[key] = (count, window_start)
            remaining = max(0, self._window - int(now - window_start))
        return count <= self._limit, remaining

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        key = self._client_key(request)
        allowed, retry_after = self._is_allowed(key)
        if not allowed:
            response = problem_details_response(
                "too-many-requests",
                "Too Many Requests",
                429,
                f"Rate limit exceeded. Retry after {retry_after} seconds.",
            )
            response.headers["Retry-After"] = str(retry_after)
            return response
        return await call_next(request)
