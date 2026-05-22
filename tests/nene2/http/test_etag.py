"""generate_etag / check_not_modified / check_precondition のテスト。"""

import pytest
from starlette.requests import Request

from nene2.http import check_not_modified, check_precondition, generate_etag

# ---------------------------------------------------------------------------
# generate_etag
# ---------------------------------------------------------------------------


def test_generate_etag_returns_quoted_hex() -> None:
    result = generate_etag({"key": "value"})
    assert result.startswith('"')
    assert result.endswith('"')
    inner = result[1:-1]
    assert len(inner) == 32
    assert all(c in "0123456789abcdef" for c in inner)


def test_generate_etag_same_data_same_result() -> None:
    data = {"article_id": 1, "title": "Hello"}
    assert generate_etag(data) == generate_etag(data)


def test_generate_etag_different_data_different_result() -> None:
    assert generate_etag({"title": "A"}) != generate_etag({"title": "B"})


def test_generate_etag_key_order_independent() -> None:
    d1 = {"b": 2, "a": 1}
    d2 = {"a": 1, "b": 2}
    assert generate_etag(d1) == generate_etag(d2)


def test_generate_etag_list_input() -> None:
    result = generate_etag([1, 2, 3])
    assert result.startswith('"')
    assert result.endswith('"')


def test_generate_etag_string_input() -> None:
    result = generate_etag("hello world")
    assert result.startswith('"')
    assert result.endswith('"')


def test_generate_etag_bytes_input() -> None:
    result = generate_etag(b"raw bytes")
    assert result.startswith('"')
    assert result.endswith('"')


def test_generate_etag_string_and_bytes_equivalent() -> None:
    assert generate_etag("hello") == generate_etag(b"hello")


# ---------------------------------------------------------------------------
# check_not_modified helpers
# ---------------------------------------------------------------------------


def _make_request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


# ---------------------------------------------------------------------------
# check_not_modified
# ---------------------------------------------------------------------------


def test_check_not_modified_matching_etag_returns_304() -> None:
    etag = '"abc123"'
    request = _make_request({"If-None-Match": etag})
    response = check_not_modified(request, etag)
    assert response is not None
    assert response.status_code == 304
    assert response.headers["etag"] == etag


def test_check_not_modified_no_header_returns_none() -> None:
    request = _make_request({})
    assert check_not_modified(request, '"abc123"') is None


def test_check_not_modified_different_etag_returns_none() -> None:
    request = _make_request({"If-None-Match": '"old"'})
    assert check_not_modified(request, '"new"') is None


def test_check_not_modified_last_modified_match_returns_304() -> None:
    ts = "2026-05-20T12:00:00Z"
    request = _make_request({"If-Modified-Since": ts})
    response = check_not_modified(request, '"xyz"', last_modified=ts)
    assert response is not None
    assert response.status_code == 304
    assert response.headers["last-modified"] == ts


def test_check_not_modified_last_modified_older_returns_none() -> None:
    request = _make_request({"If-Modified-Since": "2026-01-01T00:00:00Z"})
    response = check_not_modified(request, '"xyz"', last_modified="2026-05-20T12:00:00Z")
    assert response is None


def test_check_not_modified_304_without_last_modified_header() -> None:
    etag = '"abc"'
    request = _make_request({"If-None-Match": etag})
    response = check_not_modified(request, etag)
    assert response is not None
    assert "last-modified" not in response.headers


# ---------------------------------------------------------------------------
# check_precondition
# ---------------------------------------------------------------------------


def test_check_precondition_no_header_returns_428() -> None:
    request = _make_request({})
    response = check_precondition(request, '"v1"')
    assert response is not None
    assert response.status_code == 428


def test_check_precondition_no_header_require_false_returns_none() -> None:
    request = _make_request({})
    assert check_precondition(request, '"v1"', require=False) is None


def test_check_precondition_wildcard_returns_none() -> None:
    request = _make_request({"If-Match": "*"})
    assert check_precondition(request, '"v1"') is None


def test_check_precondition_matching_etag_returns_none() -> None:
    request = _make_request({"If-Match": '"v1"'})
    assert check_precondition(request, '"v1"') is None


def test_check_precondition_mismatched_etag_returns_412() -> None:
    request = _make_request({"If-Match": '"v1"'})
    response = check_precondition(request, '"v2"')
    assert response is not None
    assert response.status_code == 412


@pytest.mark.parametrize(
    ("if_match", "current", "expected"),
    [
        ('"v1"', '"v1"', None),
        ('"v1"', '"v2"', 412),
        ("*", '"v99"', None),
        ("", '"v1"', 428),
    ],
)
def test_check_precondition_parametrize(if_match: str, current: str, expected: int | None) -> None:
    headers = {"If-Match": if_match} if if_match else {}
    request = _make_request(headers)
    response = check_precondition(request, current)
    if expected is None:
        assert response is None
    else:
        assert response is not None
        assert response.status_code == expected
