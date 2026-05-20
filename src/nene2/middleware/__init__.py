"""NENE2 middleware pipeline."""

from .domain_exception import DomainExceptionHandlerProtocol, SimpleDomainHandler
from .error_handler import ErrorHandlerMiddleware, request_validation_error_handler
from .request_id import RequestIdMiddleware, get_request_id, request_id_var
from .request_logging import RequestLoggingMiddleware
from .request_size_limit import RequestSizeLimitMiddleware
from .security_headers import SecurityHeadersMiddleware
from .setup import setup_middlewares
from .throttle import ThrottleMiddleware

__all__ = [
    "DomainExceptionHandlerProtocol",
    "SimpleDomainHandler",
    "ErrorHandlerMiddleware",
    "request_validation_error_handler",
    "RequestIdMiddleware",
    "get_request_id",
    "RequestLoggingMiddleware",
    "RequestSizeLimitMiddleware",
    "SecurityHeadersMiddleware",
    "setup_middlewares",
    "ThrottleMiddleware",
    "request_id_var",
]
