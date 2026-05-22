"""query_string / query_int / query_bool / query_comma_separated / query_array のテスト。"""

import pytest
from starlette.requests import Request

from nene2.http import query_array, query_bool, query_comma_separated, query_int, query_string


def _make_request(query: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": query.encode(),
        "headers": [],
    }
    return Request(scope)


# ---------------------------------------------------------------------------
# query_string
# ---------------------------------------------------------------------------


def test_query_string_returns_value() -> None:
    assert query_string(_make_request("name=alice"), "name") == "alice"


def test_query_string_returns_default_when_missing() -> None:
    assert query_string(_make_request(""), "name") is None
    assert query_string(_make_request(""), "name", "anon") == "anon"


# ---------------------------------------------------------------------------
# query_int
# ---------------------------------------------------------------------------


def test_query_int_parses_integer() -> None:
    assert query_int(_make_request("page=3"), "page") == 3


def test_query_int_returns_default_on_missing() -> None:
    assert query_int(_make_request(""), "page") is None
    assert query_int(_make_request(""), "page", 1) == 1


def test_query_int_returns_default_on_invalid() -> None:
    assert query_int(_make_request("page=abc"), "page") is None
    assert query_int(_make_request("page=abc"), "page", 0) == 0


# ---------------------------------------------------------------------------
# query_bool
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw", ["true", "True", "TRUE", "1", "yes", "Yes"])
def test_query_bool_true_values(raw: str) -> None:
    assert query_bool(_make_request(f"flag={raw}"), "flag") is True


@pytest.mark.parametrize("raw", ["false", "False", "FALSE", "0", "no", "No"])
def test_query_bool_false_values(raw: str) -> None:
    assert query_bool(_make_request(f"flag={raw}"), "flag") is False


def test_query_bool_returns_default_on_missing() -> None:
    assert query_bool(_make_request(""), "flag") is None
    assert query_bool(_make_request(""), "flag", True) is True


def test_query_bool_returns_default_on_invalid() -> None:
    assert query_bool(_make_request("flag=maybe"), "flag") is None


# ---------------------------------------------------------------------------
# query_comma_separated
# ---------------------------------------------------------------------------


def test_query_comma_separated_returns_list() -> None:
    result = query_comma_separated(_make_request("tags=a,b,c"), "tags")
    assert result == ["a", "b", "c"]


def test_query_comma_separated_strips_whitespace() -> None:
    result = query_comma_separated(_make_request("tags=a%2C+b%2C+c"), "tags")
    assert result == ["a", "b", "c"]


def test_query_comma_separated_returns_none_when_missing() -> None:
    assert query_comma_separated(_make_request(""), "tags") is None


def test_query_comma_separated_skips_empty_parts() -> None:
    result = query_comma_separated(_make_request("tags=a,,b,"), "tags")
    assert result == ["a", "b"]


# ---------------------------------------------------------------------------
# query_array
# ---------------------------------------------------------------------------


def test_query_array_returns_multiple_values() -> None:
    result = query_array(_make_request("ids=1&ids=2&ids=3"), "ids")
    assert result == ["1", "2", "3"]


def test_query_array_returns_none_when_missing() -> None:
    assert query_array(_make_request(""), "ids") is None


def test_query_array_returns_single_value_as_list() -> None:
    result = query_array(_make_request("ids=42"), "ids")
    assert result == ["42"]
