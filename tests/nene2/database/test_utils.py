"""Tests for nene2.database.parse_db_datetime."""

from datetime import UTC, datetime

import pytest

from nene2.database import parse_db_datetime


def test_parses_sqlite_space_separated_string() -> None:
    result = parse_db_datetime("2026-05-20 12:34:56")
    assert result == datetime(2026, 5, 20, 12, 34, 56, tzinfo=UTC)
    assert result.tzinfo is UTC


def test_parses_iso_t_separated_string() -> None:
    result = parse_db_datetime("2026-05-20T12:34:56")
    assert result == datetime(2026, 5, 20, 12, 34, 56, tzinfo=UTC)


def test_parses_naive_datetime_object() -> None:
    naive = datetime(2026, 5, 20, 12, 34, 56)
    result = parse_db_datetime(naive)
    assert result.tzinfo is UTC
    assert result == datetime(2026, 5, 20, 12, 34, 56, tzinfo=UTC)


def test_preserves_aware_datetime_object() -> None:
    aware = datetime(2026, 5, 20, 12, 34, 56, tzinfo=UTC)
    result = parse_db_datetime(aware)
    assert result is aware


def test_result_is_always_utc_aware() -> None:
    for value in [
        "2026-01-01 00:00:00",
        "2026-01-01T00:00:00",
        datetime(2026, 1, 1),
    ]:
        result = parse_db_datetime(value)
        assert result.tzinfo is not None, f"Expected UTC-aware for {value!r}"


@pytest.mark.parametrize(
    "value",
    [
        "2026-05-20 00:00:00",
        "2026-12-31 23:59:59",
        "2020-02-29 12:00:00",
    ],
)
def test_parses_various_sqlite_timestamp_formats(value: str) -> None:
    result = parse_db_datetime(value)
    assert isinstance(result, datetime)
    assert result.tzinfo is UTC
