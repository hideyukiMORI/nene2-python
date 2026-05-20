"""Tests for problem_details_response() and configure_problem_details()."""

import pytest

from nene2.http import configure_problem_details, problem_details_response, reset_problem_details


@pytest.fixture(autouse=True)
def reset_configured_base_url() -> None:
    """Reset module-level configured base_url between tests."""
    reset_problem_details()
    yield
    reset_problem_details()


def test_problem_details_response_uses_default_base_url() -> None:
    r = problem_details_response("not-found", "Not Found", 404)
    body = r.body
    assert b"nene2.dev/problems/not-found" in body


def test_problem_details_response_accepts_explicit_base_url() -> None:
    r = problem_details_response(
        "not-found", "Not Found", 404, base_url="https://example.com/errors/"
    )
    body = r.body
    assert b"example.com/errors/not-found" in body


def test_configure_problem_details_sets_project_wide_base_url() -> None:
    configure_problem_details("https://api.myapp.com/problems/")
    r = problem_details_response("not-found", "Not Found", 404)
    body = r.body
    assert b"api.myapp.com/problems/not-found" in body


def test_explicit_base_url_overrides_configured_base_url() -> None:
    configure_problem_details("https://api.myapp.com/problems/")
    r = problem_details_response("not-found", "Not Found", 404, base_url="https://override.com/p/")
    body = r.body
    assert b"override.com/p/not-found" in body


def test_problem_details_response_sets_problem_json_media_type() -> None:
    r = problem_details_response("error", "Error", 500)
    assert r.media_type == "application/problem+json"


def test_problem_details_response_includes_status_and_title() -> None:
    r = problem_details_response("not-found", "Not Found", 404)
    assert r.status_code == 404
    assert b'"title":"Not Found"' in r.body


def test_problem_details_response_includes_detail_when_provided() -> None:
    r = problem_details_response("not-found", "Not Found", 404, detail="Resource not found")
    assert b'"detail":"Resource not found"' in r.body


def test_problem_details_response_includes_extra_fields() -> None:
    r = problem_details_response("not-found", "Not Found", 404, extra={"resource_id": 42})
    assert b'"resource_id":42' in r.body


def test_reset_problem_details_restores_default_base_url() -> None:
    configure_problem_details("https://custom.example.com/problems/")
    reset_problem_details()
    r = problem_details_response("not-found", "Not Found", 404)
    assert b"nene2.dev/problems/not-found" in r.body


def test_reset_problem_details_is_idempotent() -> None:
    reset_problem_details()
    reset_problem_details()
    r = problem_details_response("not-found", "Not Found", 404)
    assert b"nene2.dev/problems/not-found" in r.body
