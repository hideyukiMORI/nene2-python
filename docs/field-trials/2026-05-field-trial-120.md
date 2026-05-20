# Field Trial 120: dataclasses.field 高度な使い方

## テーマ

`dataclasses.field()` の `compare=False`, `repr=False`, `metadata`, `default_factory` を活用して、
ドメインエンティティの設計を精緻化するパターンを検証する。
`frozen=True, slots=True` のイミュータブルエンティティを例に使用する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft120-dataclass-field/` に以下を実装:

- `Money` — `default_factory` で通貨デフォルト値、`metadata` で説明を付与
- `OrderItem` — `internal_note` を `compare=False, repr=False` で等価比較・repr から除外
- `Order` — `order_id` を `default_factory=lambda: str(uuid.uuid4())`, `updated_at` を `compare=False`
- 13 テスト通過（修正後）

## テスト結果

1 件修正後、全 13 テスト通過。

## Friction Points

### FP1: `compare=False` を検証するテストで `default_factory` フィールドが干渉する

**状況**: `Order` の `updated_at` が `compare=False` であることを検証するテストで、
`created_at` も `default_factory=lambda: datetime.now(UTC)` を使っているため、
同一インスタンスを作っても `created_at` が異なりテストが失敗した。

```python
# ❌ created_at が異なるため等価にならない
order_a = Order(order_id="same-id", items=items)
order_b = Order(order_id="same-id", items=items, updated_at=later)
assert order_a == order_b  # FAIL: created_at が違う

# ✅ created_at を明示して揃える
now = datetime.now(UTC)
order_a = Order(order_id="same-id", items=items, created_at=now, updated_at=now)
order_b = Order(order_id="same-id", items=items, created_at=now, updated_at=later)
assert order_a == order_b  # OK
```

**影響**: 小。`default_factory` フィールドが複数ある dataclass の等価テストでは、
テストしたいフィールド以外の `default_factory` フィールドを明示的に揃える必要がある。

## 観察

### O1: `compare=False` で特定フィールドを等価比較から除外できる

```python
@dataclass(frozen=True, slots=True)
class OrderItem:
    product_id: int
    name: str
    internal_note: str = field(default="", compare=False)  # 等価比較に含まれない

item_a = OrderItem(product_id=1, name="Apple", internal_note="VIP")
item_b = OrderItem(product_id=1, name="Apple", internal_note="")
assert item_a == item_b  # True — internal_note は無視される
```

監査ログ・メモ欄・タイムスタンプなど「同一性に関係ないフィールド」を除外できる。

### O2: `repr=False` でログ・デバッグから機密フィールドを隠せる

```python
internal_note: str = field(default="", compare=False, repr=False)

item = OrderItem(product_id=1, name="Apple", quantity=1, unit_price=Money(100), internal_note="secret")
repr(item)
# → "OrderItem(product_id=1, name='Apple', quantity=1, unit_price=Money(amount=100, currency='JPY'))"
# "secret" は含まれない
```

structlog 等でエンティティを直接ログに出力した場合に機密情報が漏れない。

### O3: `field(metadata=...)` でフィールドのメタデータを記録できる

```python
currency: str = field(default="JPY", metadata={"description": "ISO 4217 currency code"})

# 実行時に取得可能
from dataclasses import fields
for f in fields(Money):
    if f.name == "currency":
        print(f.metadata["description"])  # "ISO 4217 currency code"
```

OpenAPI スキーマ生成・ドキュメント自動化・フォームバリデーション等に活用できる。

## まとめ

FP1（default_factory フィールドが compare テストに干渉）を記録。
`compare=False`, `repr=False`, `metadata` は nene2 のイミュータブルエンティティ設計で
活用できる重要なオプション群。
