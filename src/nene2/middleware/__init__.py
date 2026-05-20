"""NENE2 middleware pipeline."""

from .domain_exception import DomainExceptionHandlerProtocol, SimpleDomainHandler
from .error_handler import ErrorHandlerMiddleware
from .request_id import RequestIdMiddleware, get_request_id, request_id_var
from .request_logging import RequestLoggingMiddleware
from .request_size_limit import RequestSizeLimitMiddleware
from .security_headers import SecurityHeadersMiddleware
from .throttle import ThrottleMiddleware

__all__ = [
    "DomainExceptionHandlerProtocol",
    "SimpleDomainHandler",
    "ErrorHandlerMiddleware",
    "RequestIdMiddleware",
    "get_request_id",
    "RequestLoggingMiddleware",
    "RequestSizeLimitMiddleware",
    "SecurityHeadersMiddleware",
    "ThrottleMiddleware",
    "request_id_var",
]
