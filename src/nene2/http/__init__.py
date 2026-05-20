"""HTTP helpers — JSON responses, pagination, problem details, health."""

from .etag import generate_etag
from .health import (
    AsyncCompositeHealthCheck,
    AsyncHealthCheckProtocol,
    CompositeHealthCheck,
    HealthCheckProtocol,
    HealthStatus,
)
from .pagination import PaginationDep, PaginationQuery, PaginationQueryParser, PaginationResponse
from .problem_details import (
    PROBLEM_DETAILS_BASE_URL,
    configure_problem_details,
    problem_details_response,
    reset_problem_details,
)

__all__ = [
    "generate_etag",
    "AsyncCompositeHealthCheck",
    "AsyncHealthCheckProtocol",
    "CompositeHealthCheck",
    "HealthCheckProtocol",
    "HealthStatus",
    "PaginationDep",
    "PaginationQuery",
    "PaginationQueryParser",
    "PaginationResponse",
    "PROBLEM_DETAILS_BASE_URL",
    "configure_problem_details",
    "problem_details_response",
    "reset_problem_details",
]
