"""Tests for nene2.cache.TtlCache."""

import time

import pytest

from nene2.cache import TtlCache


def test_set_and_get_returns_value() -> None:
    cache = TtlCache(ttl_seconds=60.0)
    cache.set("key", {"data": 42})
    assert cache.get("key") == {"data": 42}


def test_get_missing_key_returns_none() -> None:
    cache = TtlCache(ttl_seconds=60.0)
    assert cache.get("nonexistent") is None


def test_expired_entry_returns_none() -> None:
    cache = TtlCache(ttl_seconds=0.01)
    cache.set("key", "value")
    time.sleep(0.02)
    assert cache.get("key") is None


def test_expired_entry_is_removed_from_store() -> None:
    cache = TtlCache(ttl_seconds=0.01)
    cache.set("key", "value")
    time.sleep(0.02)
    cache.get("key")  # TTL 切れでエントリ削除
    assert cache.size() == 0


def test_delete_removes_entry() -> None:
    cache = TtlCache(ttl_seconds=60.0)
    cache.set("key", "value")
    cache.delete("key")
    assert cache.get("key") is None


def test_delete_missing_key_does_not_raise() -> None:
    cache = TtlCache(ttl_seconds=60.0)
    cache.delete("nonexistent")  # should not raise


def test_clear_removes_all_entries() -> None:
    cache = TtlCache(ttl_seconds=60.0)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.size() == 0


def test_size_excludes_expired_entries() -> None:
    cache = TtlCache(ttl_seconds=0.01)
    cache.set("expired", "value")
    time.sleep(0.02)
    cache.set("fresh", "value")
    assert cache.size() == 1


def test_overwrite_resets_ttl() -> None:
    cache = TtlCache(ttl_seconds=60.0)
    cache.set("key", "old")
    cache.set("key", "new")
    assert cache.get("key") == "new"


@pytest.mark.parametrize("value", [None, 0, "", [], {}, False])
def test_falsy_values_are_stored_correctly(value: object) -> None:
    cache = TtlCache(ttl_seconds=60.0)
    cache.set("key", value)
    assert cache.get("key") == value
    assert cache.size() == 1
