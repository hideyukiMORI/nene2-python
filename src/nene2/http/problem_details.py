"""RFC 9457 Problem Details response factory.

Equivalent to PHP Nene2\\Error\\ProblemDetailsResponseFactory.
"""

from typing import Any

from fastapi.responses import JSONResponse

PROBLEM_DETAILS_BASE_URL = "https://nene2.dev/problems/"

_configured_base_url: str | None = None


def configure_problem_details(base_url: str) -> None:
    """Set the project-wide default base_url for problem_details_response().

    Call once at application startup to avoid passing base_url on every call.

    Example::

        from nene2.http import configure_problem_details

        configure_problem_details("https://api.myapp.com/problems/")
    """
    global _configured_base_url  # noqa: PLW0603
    _configured_base_url = base_url


def problem_details_response(
    problem_type: str,
    title: str,
    status: int,
    detail: str | None = None,
    extra: dict[str, Any] | None = None,
    *,
    base_url: str | None = None,
) -> JSONResponse:
    """Build an RFC 9457 Problem Details JSON response.

    ``base_url`` resolution order:
    1. Explicit ``base_url`` argument
    2. Value set by :func:`configure_problem_details`
    3. Built-in default (``PROBLEM_DETAILS_BASE_URL``)
    """
    resolved_base_url = base_url or _configured_base_url or PROBLEM_DETAILS_BASE_URL
    body: dict[str, Any] = {
        "type": resolved_base_url + problem_type,
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
