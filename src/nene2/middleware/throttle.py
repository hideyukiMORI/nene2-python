"""Fixed-window rate limiting middleware.

Tracks request counts per client IP via a pluggable storage backend.
The default backend (``InMemoryRateLimitStorage``) works in a single process.
For multi-process or multi-container deployments, supply a Redis-backed
implementation of ``RateLimitStorageProtocol``.

All responses include ``X-RateLimit-Limit``, ``X-RateLimit-Remaining``, and
``X-RateLimit-Reset`` headers so clients can adapt their request rate.
Exceeding the limit returns 429 with a ``Retry-After`` header.

.. warning::
    ``X-Forwarded-For`` is trusted as-is when present.  In environments
    **without** a trusted reverse proxy this header can be spoofed by clients,
    allowing them to bypass the rate limit.  Deploy behind a proxy that strips
    or overwrites the header (e.g. nginx ``proxy_set_header X-Forwarded-For
    $remote_addr``) before enabling this middleware in production.
"""

import threading
import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response

_DEFAULT_LIMIT = 60
_DEFAULT_WINDOW = 60  # seconds


@runtime_checkable
class RateLimitStorageProtocol(Protocol):
    """Pluggable backend for ``ThrottleMiddleware``.

    Implementations must atomically increment a counter and return the
    post-increment count together with the window start timestamp.

    The ``acquire`` method is called once per request and must be
    thread-safe (or use a distributed lock for shared backends).
    """

    def acquire(self, key: str, now: float, window: float) -> tuple[int, float]:
        """Increment the counter for *key* and return ``(count, window_start)``.

        When the current window has expired (``now - window_start >= window``),
        the counter resets to 1 and ``window_start`` is set to ``now``.
        """
        ...  # pragma: no cover


class InMemoryRateLimitStorage:
    """Thread-safe in-memory fixed-window counter.

    .. warning:: **Single-process only.**
        Each process maintains its own counters.  When running multiple
        workers or containers the effective limit is ``limit × worker_count``.
        Use a shared store (Redis) for multi-process deployments.
    """

    def __init__(self) -> None:
        self._counts: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()
        self._last_cleanup: float = 0.0

    def acquire(self, key: str, now: float, window: float) -> tuple[int, float]:
        with self._lock:
            self._maybe_evict(now, window)
            count, window_start = self._counts.get(key, (0, now))
            if now - window_start >= window:
                count, window_start = 0, now
            count += 1
            self._counts[key] = (count, window_start)
        return (count, window_start)

    def _maybe_evict(self, now: float, window: float) -> None:
        if now - self._last_cleanup < window:
            return
        self._last_cleanup = now
        cutoff = now - window
        stale = [k for k, (_, ws) in self._counts.items() if ws < cutoff]
        for k in stale:
            del self._counts[k]


@dataclass(frozen=True, slots=True)
class _RateInfo:
    allowed: bool
    remaining: int
    retry_after: int
    reset_at: int  # Unix timestamp


class ThrottleMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limiter keyed by client IP.

    Adds ``X-RateLimit-Limit``, ``X-RateLimit-Remaining``, and
    ``X-RateLimit-Reset`` headers to every response so clients can monitor
    their quota.  On 429, also adds ``Retry-After``.

    Pass a custom ``storage`` to swap in a Redis or other shared backend::

        app.add_middleware(
            ThrottleMiddleware,
            limit=100,
            window=60,
            storage=MyRedisStorage(redis_client),
        )

    Use ``path_limits`` to apply stricter limits on specific paths::

        app.add_middleware(
            ThrottleMiddleware,
            limit=100,
            window=60,
            path_limits={"/api/expensive": 10, "/api/search": 30},
            exclude_paths=["/health", "/docs", "/openapi.json"],
        )

    Path-limited endpoints are tracked independently from the global counter
    (the key includes the path, so ``/api/expensive`` quota is separate from
    the default quota for other paths).

    .. note:: **Fixed-window burst at boundaries.**
        Fixed-window counting can pass up to ``2 × limit`` requests in a
        short burst when requests arrive just before and just after a window
        boundary.  If you need protection against burst traffic, consider
        sliding-window rate limiting at the proxy layer.
    """

    def __init__(
        self,
        app: object,
        *,
        limit: int = _DEFAULT_LIMIT,
        window: int = _DEFAULT_WINDOW,
        path_limits: dict[str, int] | None = None,
        exclude_paths: list[str] | None = None,
        storage: RateLimitStorageProtocol | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._limit = limit
        self._window = window
        self._path_limits: dict[str, int] = path_limits or {}
        self._exclude_paths = set(exclude_paths or [])
        self._storage: RateLimitStorageProtocol = storage or InMemoryRateLimitStorage()

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check_rate(self, key: str, limit: int) -> _RateInfo:
        now = time.monotonic()
        wall_now = int(time.time())
        count, window_start = self._storage.acquire(key, now, self._window)
        elapsed = int(now - window_start)
        retry_after = max(0, self._window - elapsed)
        reset_at = wall_now + retry_after
        remaining = max(0, limit - count)
        return _RateInfo(
            allowed=count <= limit,
            remaining=remaining,
            retry_after=retry_after,
            reset_at=reset_at,
        )

    def _apply_rate_headers(self, response: Response, info: _RateInfo, limit: int) -> None:
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(info.remaining)
        response.headers["X-RateLimit-Reset"] = str(info.reset_at)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path in self._exclude_paths:
            return await call_next(request)
        client = self._client_key(request)
        if path in self._path_limits:
            effective_limit = self._path_limits[path]
            key = f"{client}:{path}"
        else:
            effective_limit = self._limit
            key = client
        info = self._check_rate(key, effective_limit)
        if not info.allowed:
            error_response = problem_details_response(
                "too-many-requests",
                "Too Many Requests",
                429,
                f"Rate limit exceeded. Retry after {info.retry_after} seconds.",
            )
            error_response.headers["Retry-After"] = str(info.retry_after)
            self._apply_rate_headers(error_response, info, effective_limit)
            return error_response
        response = await call_next(request)
        self._apply_rate_headers(response, info, effective_limit)
        return response
