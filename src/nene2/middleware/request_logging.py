"""Request logging middleware using structlog."""

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .request_id import request_id_var

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log each request and response with method, path, status, and duration.

    Args:
        exclude_paths: Paths to skip logging for (e.g. ``["/health"]``).
            Useful for high-frequency health-check endpoints where log noise is unwanted.
    """

    def __init__(self, app: object, exclude_paths: list[str] | None = None) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._exclude_paths = set(exclude_paths or [])

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._exclude_paths:
            return await call_next(request)

        start = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id_var.get(),
            method=request.method,
            path=request.url.path,
        )
        logger.info("request.received")
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        structlog.contextvars.bind_contextvars(
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        logger.info("request.completed")
        return response
