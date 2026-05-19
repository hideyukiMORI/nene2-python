"""RFC 9457 Problem Details response factory.

Equivalent to PHP Nene2\\Error\\ProblemDetailsResponseFactory.
"""

from typing import Any

from fastapi.responses import JSONResponse

PROBLEM_DETAILS_BASE_URL = "https://nene2.dev/problems/"


def problem_details_response(
    problem_type: str,
    title: str,
    status: int,
    detail: str | None = None,
    extra: dict[str, Any] | None = None,
    *,
    base_url: str = PROBLEM_DETAILS_BASE_URL,
) -> JSONResponse:
    """Build an RFC 9457 Problem Details JSON response."""
    body: dict[str, Any] = {
        "type": base_url + problem_type,
        "title": title,
        "status": status,
    }
    if detail:
        body["detail"] = detail
    if extra:
        body.update(extra)

    return JSONResponse(
        content=body,
        status_code=status,
        media_type="application/problem+json",
    )
