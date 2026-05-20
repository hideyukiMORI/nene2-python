"""TTL 付きインメモリキャッシュ."""

import time
from dataclasses import dataclass, field


@dataclass
class _Entry[V]:
    value: V
    expires_at: float


@dataclass
class TtlCache[V]:
    """TTL 付きインメモリキャッシュ。

    asyncio コンテキストでの利用を想定。Python GIL により dict 操作は
    アトミックで安全だが、get-then-set のような複合操作は排他しない。

    Args:
        ttl_seconds: キャッシュエントリの生存時間（秒）。

    Example:
        cache: TtlCache[dict[str, object]] = TtlCache(ttl_seconds=60.0)
        cache.set("key", {"data": 42})
        value = cache.get("key")
    """

    ttl_seconds: float
    _store: dict[str, _Entry[V]] = field(default_factory=dict, init=False, repr=False)

    def get(self, key: str) -> V | None:
        """キーに対応する値を返す。TTL 切れの場合は None を返してエントリを削除する。"""
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: V) -> None:
        """キーと値を TTL 付きで格納する。"""
        self._store[key] = _Entry(value=value, expires_at=time.monotonic() + self.ttl_seconds)

    def delete(self, key: str) -> None:
        """キーに対応するエントリを削除する。存在しなくても例外は発生しない。"""
        self._store.pop(key, None)

    def clear(self) -> None:
        """すべてのエントリを削除する。"""
        self._store.clear()

    def size(self) -> int:
        """TTL 切れを除いた有効なエントリ数を返す。"""
        now = time.monotonic()
        return sum(1 for e in self._store.values() if e.expires_at > now)
