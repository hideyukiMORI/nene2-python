"""Error handler middleware.

Equivalent to PHP Nene2\\Middleware\\ErrorHandlerMiddleware.
Maps known exceptions to Problem Details responses; all others → 500.
"""

import logging
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response
from nene2.validation.exceptions import ValidationError, ValidationException

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
    """Catch-all error handler that maps exceptions to Problem Details responses.

    **Recommended usage** — use :meth:`install` instead of ``add_middleware`` directly.
    ``install`` also registers ``request_validation_error_handler`` so that
    FastAPI's Pydantic validation errors (422) are formatted as nene2 Problem Details::

        ErrorHandlerMiddleware.install(app)
        # Equivalent to:
        #   app.add_middleware(ErrorHandlerMiddleware)
        #   app.add_exception_handler(RequestValidationError, request_validation_error_handler)

    Using ``add_middleware`` directly works, but FastAPI's ``RequestValidationError``
    will be returned in Pydantic's default format rather than nene2 Problem Details.
    """

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

    @classmethod
    def install(
        cls,
        app: object,
        *,
        debug: bool = False,
        domain_handlers: list[DomainExceptionHandlerProtocol] | None = None,
    ) -> None:
        """Add this middleware and register the nene2 validation error handler.

        Registers both ``ErrorHandlerMiddleware`` and ``request_validation_error_handler``
        so that all 422 responses (Pydantic body validation and ``ValidationException``)
        are formatted as nene2 Problem Details::

            from nene2.middleware import ErrorHandlerMiddleware

            app = FastAPI()
            ErrorHandlerMiddleware.install(app)

        Equivalent to::

            app.add_middleware(ErrorHandlerMiddleware, debug=debug, domain_handlers=domain_handlers)
            app.add_exception_handler(RequestValidationError, request_validation_error_handler)
        """
        if not isinstance(app, Starlette):
            raise TypeError(f"app must be a Starlette/FastAPI instance, got {type(app)!r}")
        app.add_middleware(cls, debug=debug, domain_handlers=domain_handlers)
        app.add_exception_handler(RequestValidationError, request_validation_error_handler)

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


async def request_validation_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Convert FastAPI RequestValidationError to nene2 Problem Details (422).

    Register with FastAPI to replace the default Pydantic validation error format::

        from fastapi.exceptions import RequestValidationError
        from nene2.middleware.error_handler import request_validation_error_handler

        app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    """
    if not isinstance(exc, RequestValidationError):
        raise TypeError(f"Expected RequestValidationError, got {type(exc)}")

    errors: list[ValidationError] = []
    for raw in exc.errors():
        loc = raw.get("loc", ())
        field = ".".join(str(part) for part in loc if part != "body") or "request"
        message = str(raw.get("msg", "Invalid value."))
        code = str(raw.get("type", "invalid"))
        errors.append(ValidationError(field=field or "request", message=message, code=code))

    return problem_details_response(
        "validation-failed",
        "Validation Failed",
        422,
        "The request contains invalid values.",
        extra={"errors": [e.to_dict() for e in errors]},
    )
