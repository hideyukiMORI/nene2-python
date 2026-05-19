"""Error handler middleware.

Equivalent to PHP Nene2\\Middleware\\ErrorHandlerMiddleware.
Maps known exceptions to Problem Details responses; all others → 500.
"""

import logging
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response
from nene2.validation.exceptions import ValidationException

from .domain_exception import DomainExceptionHandlerProtocol

_ASGIApp = Callable[
    [
        MutableMapping[str, Any],
        Callable[[], Awaitable[MutableMapping[str, Any]]],
        Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ],
    Awaitable[None],
]

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch-all error handler that maps exceptions to Problem Details responses."""

    def __init__(
        self,
        app: _ASGIApp,
        *,
        debug: bool = False,
        domain_handlers: list[DomainExceptionHandlerProtocol] | None = None,
    ) -> None:
        super().__init__(app)
        self.debug = debug
        self._domain_handlers: list[DomainExceptionHandlerProtocol] = domain_handlers or []

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except ValidationException as exc:
            return problem_details_response(
                "validation-failed",
                "Validation Failed",
                422,
                "The request contains invalid values.",
                extra={"errors": [e.to_dict() for e in exc.errors]},
            )
        except Exception as exc:
            for handler in self._domain_handlers:
                if handler.handles(exc):
                    return handler.handle(exc)
            logger.exception("Unhandled exception")
            detail = str(exc) if self.debug else "The server encountered an unexpected condition."
            return problem_details_response(
                "internal-server-error",
                "Internal Server Error",
                500,
                detail,
            )

    @staticmethod
    async def handle_validation_exception(_request: Request, exc: Exception) -> JSONResponse:
        if not isinstance(exc, ValidationException):
            raise TypeError(f"Expected ValidationException, got {type(exc)}")
        return problem_details_response(
            "validation-failed",
            "Validation Failed",
            422,
            "The request contains invalid values.",
            extra={"errors": [e.to_dict() for e in exc.errors]},
        )
