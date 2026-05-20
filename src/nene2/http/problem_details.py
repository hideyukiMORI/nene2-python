"""RFC 9457 Problem Details response factory.

Equivalent to PHP Nene2\\Error\\ProblemDetailsResponseFactory.
"""

from typing import Any

from fastapi.responses import JSONResponse

PROBLEM_DETAILS_BASE_URL = "https://nene2.dev/problems/"
_RESERVED_FIELDS = frozenset({"type", "title", "status", "detail"})

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


def reset_problem_details() -> None:
    """Reset the base_url configured by configure_problem_details().

    Intended for use in tests only. Restores the default behaviour of
    falling back to ``PROBLEM_DETAILS_BASE_URL``.

    Example::

        import pytest
        from nene2.http import reset_problem_details


        @pytest.fixture(autouse=True)
        def _reset():
            yield
            reset_problem_details()
    """
    global _configured_base_url  # noqa: PLW0603
    _configured_base_url = None


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

    Args:
        problem_type: Short identifier appended to ``base_url`` for the ``type`` URI.
        title:        Human-readable summary of the error.
        status:       HTTP status code.
        detail:       Optional human-readable explanation.
        extra:        Additional fields merged **at the top level** of the response body
                      (RFC 9457 extension members).  They are NOT nested under an
                      ``"extra"`` key.  For example, ``extra={"item_id": 42}`` produces
                      ``{"type": "...", "status": 404, "item_id": 42}``.
                      Raises ``ValueError`` if any key shadows a reserved field
                      (``type``, ``title``, ``status``, ``detail``).
        base_url:     Override the base URL for this call only.

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
        overlap = _RESERVED_FIELDS & extra.keys()
        if overlap:
            raise ValueError(f"extra contains reserved Problem Details fields: {sorted(overlap)}")
        body.update(extra)

    return JSONResponse(
        content=body,
        status_code=status,
        media_type="application/problem+json",
    )
