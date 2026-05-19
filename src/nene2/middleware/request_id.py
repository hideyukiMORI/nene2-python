"""Request ID middleware.

Attaches a UUID v4 X-Request-Id to every request/response.
Uses contextvars so downstream code (e.g. structlog) can read the ID.
"""

import re
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_REQUEST_ID_HEADER = "X-Request-Id"

# UUID v4 canonical form — 8-4-4-4-12 hex, version=4, variant=8/9/a/b
_UUID_V4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def _validated_request_id(value: str | None) -> str:
    """Return value if it is a valid UUID v4, otherwise generate a fresh one."""
    if value and _UUID_V4_RE.match(value):
        return value.lower()
    return str(uuid.uuid4())


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Generate or forward X-Request-Id and expose it via contextvars.

    Client-supplied X-Request-Id is accepted only when it matches UUID v4
    format, preventing log injection via arbitrary header values.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _validated_request_id(request.headers.get(_REQUEST_ID_HEADER))
        request_id_var.set(request_id)
        response = await call_next(request)
        response.headers[_REQUEST_ID_HEADER] = request_id
        return response
