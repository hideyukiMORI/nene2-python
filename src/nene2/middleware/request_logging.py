"""Request logging middleware using structlog."""

import contextlib
import time
from collections.abc import Callable

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
        extra_context: Additional key-value pairs bound to every request log entry
            (e.g. ``{"service": "my-api", "version": "1.0.0"}``).
        context_extractor: Optional callable ``(request) -> dict[str, str]`` that
            returns per-request dynamic context (e.g. user ID from JWT, tenant ID).
            The returned dict is merged into the log context for each request::

                def get_log_context(request: Request) -> dict[str, str]:
                    return {"user_id": request.headers.get("X-User-Id", "anonymous")}


                app.add_middleware(
                    RequestLoggingMiddleware,
                    context_extractor=get_log_context,
                )

            If the extractor raises an exception, it is silently skipped so that
            logging failures never break request handling.
    """

    def __init__(
        self,
        app: object,
        exclude_paths: list[str] | None = None,
        extra_context: dict[str, str] | None = None,
        context_extractor: Callable[[Request], dict[str, str]] | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._exclude_paths = set(exclude_paths or [])
        self._extra_context: dict[str, str] = extra_context or {}
        self._context_extractor = context_extractor

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._exclude_paths:
            return await call_next(request)

        start = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        dynamic_context: dict[str, str] = {}
        if self._context_extractor is not None:
            with contextlib.suppress(Exception):
                dynamic_context = self._context_extractor(request)
        structlog.contextvars.bind_contextvars(
            request_id=request_id_var.get(),
            method=request.method,
            path=request.url.path,
            **self._extra_context,
            **dynamic_context,
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
