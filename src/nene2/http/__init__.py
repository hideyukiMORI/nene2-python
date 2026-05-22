"""HTTP helpers — JSON responses, pagination, problem details, health."""

from .context import RequestScopedContext
from .etag import check_not_modified, check_precondition, generate_etag
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
from .query import query_array, query_bool, query_comma_separated, query_int, query_string

__all__ = [
    "RequestScopedContext",
    "check_not_modified",
    "check_precondition",
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
    "query_array",
    "query_bool",
    "query_comma_separated",
    "query_int",
    "query_string",
    "reset_problem_details",
]
