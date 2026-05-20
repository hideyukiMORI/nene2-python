"""generate_etag() のテスト。"""

from nene2.http import generate_etag


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
    """キーの順序が異なっても同じ ETag を生成する（sort_keys=True）。"""
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
    """str と bytes(同エンコード)は同じ ETag を生成する。"""
    assert generate_etag("hello") == generate_etag(b"hello")
