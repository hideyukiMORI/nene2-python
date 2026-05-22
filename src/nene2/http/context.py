"""RequestScopedContext — ContextVar ベースのリクエストスコープ値ホルダー。

ASGI ではリクエストごとに ContextVar が独立するため、複数リクエストで値が混在しない。
ミドルウェアで設定した値をハンドラーや下位レイヤーで型安全に取り出せる。

Example::

    tenant_id: RequestScopedContext[int] = RequestScopedContext()

    # Middleware
    tenant_id.set(extract_tenant_id(request))

    # Handler
    tid = tenant_id.get()
"""

from contextvars import ContextVar

_SENTINEL = object()


class RequestScopedContext[T]:
    """ContextVar ラッパー — ASGI リクエストスコープの型安全な値ホルダー。"""

    def __init__(self) -> None:
        self._var: ContextVar[object] = ContextVar(f"RequestScopedContext_{id(self)}")

    def set(self, value: T) -> None:
        """値を現在のコンテキストにセットする。"""
        self._var.set(value)

    def get(self) -> T:
        """値を取得する。未セットの場合は ``LookupError`` を送出する。"""
        value = self._var.get(_SENTINEL)
        if value is _SENTINEL:
            raise LookupError("RequestScopedContext value has not been set for this request.")
        return value  # type: ignore[return-value]

    def get_or_none(self) -> T | None:
        """値を取得する。未セットの場合は ``None`` を返す。"""
        value = self._var.get(_SENTINEL)
        if value is _SENTINEL:
            return None
        return value  # type: ignore[return-value]
