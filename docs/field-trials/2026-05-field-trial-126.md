# Field Trial 126: StrEnum / IntEnum の高度な活用

## テーマ

`StrEnum` の `_missing_` フックを使った大文字小文字非依存マッピングとエイリアス、
`IntEnum` のプロパティによるビジネスロジック実装、
FastAPI クエリパラメーターとしての自動変換を検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft126-enum-advanced/` に以下を実装:

- `OrderStatus(StrEnum)` — `_missing_` で大文字小文字を無視したマッチ
- `SortOrder(StrEnum)` — `_missing_` で "ascending"/"descending"/"1"/"-1" エイリアス
- `Priority(IntEnum)` — `label`, `requires_immediate_action` プロパティ
- `GET /orders` — `status`, `sort`, `min_priority` Enum クエリパラメーター
- `GET /orders/{order_id}` — Priority プロパティを使った詳細レスポンス
- `GET /enums/order-statuses` — 有効ステータス一覧
- `GET /enums/priorities` — 優先度メタデータ一覧
- 16 テスト通過

## テスト結果

全 16 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `_missing_` フックで大文字小文字非依存のマッチが実現できる

```python
class OrderStatus(StrEnum):
    PENDING = "pending"

    @classmethod
    def _missing_(cls, value: object) -> "OrderStatus | None":
        if isinstance(value, str):
            for member in cls:
                if member.value == value.lower():
                    return member
        return None
```

`OrderStatus("PENDING")` が `OrderStatus.PENDING` を返す。
`None` を返した場合、`Enum.__new__` が `ValueError` を raise する。
FastAPI のクエリパラメーターは自動的にこの変換を利用する。

### O2: `_missing_` でエイリアスマッピングを実装できる

```python
class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"

    @classmethod
    def _missing_(cls, value: object) -> "SortOrder | None":
        if isinstance(value, str):
            normalized = value.lower()
            if normalized in ("ascending", "asc", "1"):
                return cls.ASC
            if normalized in ("descending", "desc", "-1"):
                return cls.DESC
        return None
```

外部 API の値や数値フラグをフレームワーク内部の Enum にマッピングできる。

### O3: `IntEnum` にプロパティを追加してビジネスロジックを持たせられる

```python
class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @property
    def label(self) -> str:
        return self.name.title()  # "Low", "Medium", "High", "Critical"

    @property
    def requires_immediate_action(self) -> bool:
        return self >= Priority.HIGH  # HIGH と CRITICAL は True
```

数値比較（`Priority.LOW < Priority.HIGH`）が自然に使えるうえ、
ドメイン固有の意味（即時対応が必要か）もプロパティで表現できる。

### O4: FastAPI クエリパラメーターの Enum 変換は `_missing_` を通る

```python
@app.get("/orders")
def list_orders(
    status: OrderStatus | None = None,
    sort: SortOrder = SortOrder.ASC,
    min_priority: Priority = Priority.LOW,
) -> JSONResponse:
    ...
```

`GET /orders?status=PENDING` のリクエストで FastAPI が `OrderStatus("PENDING")` を
呼び出し、`_missing_` 経由で `OrderStatus.PENDING` に変換される。
`IntEnum` は `int` でも渡せる（`?min_priority=3` → `Priority.HIGH`）。

## まとめ

FT126 は摩擦ゼロ確認。`StrEnum._missing_` によるエイリアス・大文字小文字非依存マッピングと
`IntEnum` プロパティによるドメインロジック実装を確認した。
