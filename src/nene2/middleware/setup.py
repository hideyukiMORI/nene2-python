"""setup_middlewares() — register all nene2 middlewares in the correct order."""

from typing import Any

from starlette.applications import Starlette

from .domain_exception import DomainExceptionHandlerProtocol
from .error_handler import ErrorHandlerMiddleware
from .request_id import RequestIdMiddleware
from .request_logging import RequestLoggingMiddleware
from .request_size_limit import RequestSizeLimitMiddleware
from .security_headers import SecurityHeadersMiddleware
from .throttle import ThrottleMiddleware

_DEFAULT_MAX_BYTES = 1_048_576  # 1 MiB


def setup_middlewares(
    app: object,
    *,
    debug: bool = False,
    domain_handlers: list[DomainExceptionHandlerProtocol] | None = None,
    enable_request_logging: bool = True,
    throttle_limit: int | None = None,
    throttle_window: int = 60,
    throttle_path_limits: dict[str, int] | None = None,
    throttle_exclude_paths: list[str] | None = None,
    max_request_bytes: int = _DEFAULT_MAX_BYTES,
    request_size_path_limits: dict[str, int] | None = None,
    request_size_exclude_paths: list[str] | None = None,
    security_headers: bool = True,
    hsts: bool = False,
    csp: str | None = None,
    security_extra_no_csp_paths: list[str] | None = None,
) -> None:
    """Register all nene2 middlewares in the correct order.

    Starlette applies ``add_middleware`` in LIFO order (last added = outermost).
    This function adds middlewares in the correct sequence so that **all responses**
    — including 500 errors — receive ``X-Request-Id`` and security headers.

    Effective stack (outermost → innermost)::

        RequestId → SecurityHeaders → SizeLimit → Throttle → RequestLogging → ErrorHandler

    **Minimal usage** — all options have sensible defaults::

        from nene2.middleware import setup_middlewares

        app = FastAPI()
        setup_middlewares(app)

    **With customisation**::

        setup_middlewares(
            app,
            debug=True,
            throttle_limit=60,  # 60 req/min
            max_request_bytes=524_288,  # 512 KiB
            hsts=True,
        )

    **Without throttle** (pass ``throttle_limit=None``, the default)::

        setup_middlewares(app, throttle_limit=None)  # ThrottleMiddleware omitted

    **Custom domain handlers**::

        from nene2.middleware import SimpleDomainHandler

        setup_middlewares(
            app,
            domain_handlers=[
                SimpleDomainHandler(MyDomainError, "my-error", "My Error", 400),
            ],
        )

    .. note::
        This function calls :meth:`ErrorHandlerMiddleware.install` internally, which also
        registers ``request_validation_error_handler`` so Pydantic 422 errors are formatted
        as nene2 Problem Details.

    Args:
        app: The FastAPI (or Starlette) application instance.
        debug: Expose exception messages in 500 responses (development only).
        domain_handlers: Custom domain exception handlers for :class:`ErrorHandlerMiddleware`.
        enable_request_logging: Whether to include :class:`RequestLoggingMiddleware`.
        throttle_limit: Max requests per ``throttle_window`` seconds.
            Pass ``None`` (default) to skip :class:`ThrottleMiddleware`.
        throttle_window: Rate-limit window in seconds (default: 60).
        throttle_path_limits: Per-path overrides for throttle limits.
        throttle_exclude_paths: Paths excluded from throttling.

            .. warning::
                ``ThrottleMiddleware`` uses an in-memory counter that is **not
                shared across workers or pods**.  Multi-process deployments will
                see an effective limit of ``throttle_limit × worker_count``.
                See :class:`ThrottleMiddleware` for details.
        max_request_bytes: Maximum request body size in bytes (default: 1 MiB).
        request_size_path_limits: Per-path size limits.
        request_size_exclude_paths: Paths excluded from size limiting.
        security_headers: Whether to include :class:`SecurityHeadersMiddleware` (default: True).
        hsts: Enable Strict-Transport-Security header (default: False).
        csp: Custom Content-Security-Policy value. Defaults to nene2's built-in policy.
        security_extra_no_csp_paths: Additional paths to skip CSP (on top of /docs, /redoc).
    """
    if not isinstance(app, Starlette):
        raise TypeError(f"app must be a Starlette/FastAPI instance, got {type(app)!r}")

    # Add in reverse order — first added = innermost, last added = outermost.
    # Desired outermost → innermost:
    #   RequestId → SecurityHeaders → SizeLimit → Throttle → RequestLogging → ErrorHandler

    # 1. Innermost: ErrorHandlerMiddleware (also registers RequestValidationError handler)
    ErrorHandlerMiddleware.install(app, debug=debug, domain_handlers=domain_handlers)

    # 2. RequestLoggingMiddleware (optional)
    if enable_request_logging:
        app.add_middleware(RequestLoggingMiddleware)

    # 3. ThrottleMiddleware (optional)
    if throttle_limit is not None:
        throttle_kwargs: dict[str, Any] = {"limit": throttle_limit, "window": throttle_window}
        if throttle_path_limits:
            throttle_kwargs["path_limits"] = throttle_path_limits
        if throttle_exclude_paths:
            throttle_kwargs["exclude_paths"] = throttle_exclude_paths
        app.add_middleware(ThrottleMiddleware, **throttle_kwargs)

    # 4. RequestSizeLimitMiddleware
    size_kwargs: dict[str, Any] = {"max_bytes": max_request_bytes}
    if request_size_path_limits:
        size_kwargs["path_limits"] = request_size_path_limits
    if request_size_exclude_paths:
        size_kwargs["exclude_paths"] = request_size_exclude_paths
    app.add_middleware(RequestSizeLimitMiddleware, **size_kwargs)

    # 5. SecurityHeadersMiddleware (optional)
    if security_headers:
        sec_kwargs: dict[str, Any] = {"hsts": hsts}
        if csp is not None:
            sec_kwargs["csp"] = csp
        if security_extra_no_csp_paths:
            sec_kwargs["extra_no_csp_paths"] = security_extra_no_csp_paths
        app.add_middleware(SecurityHeadersMiddleware, **sec_kwargs)

    # 6. Outermost: RequestIdMiddleware
    app.add_middleware(RequestIdMiddleware)
