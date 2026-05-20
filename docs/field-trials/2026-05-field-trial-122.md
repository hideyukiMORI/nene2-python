# Field Trial 122: 型安全なインプロセス イベントバス

## テーマ

`dataclass(frozen=True)` のイベント + 型変数を使ったジェネリックなハンドラー登録・発行パターンを検証する。
ドメインイベントの publish/subscribe を型安全に実装し、FastAPI エンドポイントとの統合を確認する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft122-event-bus/` に以下を実装:

- `DomainEvent` 基底クラス（`occurred_at: datetime` を `kw_only=True` で定義）
- `OrderPlaced`, `OrderCancelled`, `PaymentReceived` — サブクラスドメインイベント
- `EventBus` — `defaultdict` ベースのハンドラーレジストリ
- `subscribe[E: DomainEvent]()` — ジェネリックメソッドで型安全なハンドラー登録
- 9 テスト通過（修正後）

## テスト結果

1 件修正後、全 9 テスト通過。

## Friction Points

### FP1: dataclass 継承で「デフォルト引数の後に非デフォルト引数」エラー

**状況**: `DomainEvent` の `occurred_at` フィールドに `default_factory` を設定し、
サブクラス `OrderPlaced` で必須フィールド（`order_id` 等）を追加したところ、
Python の dataclass 仕様でエラーになった。

```
TypeError: non-default argument 'order_id' follows default argument 'occurred_at'
```

デフォルト値を持つ親クラスフィールドの後に、サブクラスで必須フィールドを定義できない。

```python
# ❌ エラー: サブクラスの 'order_id' が親の 'occurred_at' の後に来る
@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str  # ← 必須フィールドがデフォルト後 → TypeError

# ✅ kw_only=True でキーワード専用にすることで解決（Python 3.10+）
@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC), kw_only=True)

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str  # OK — kw_only フィールドは順序制約を受けない
```

**影響**: 中。dataclass の継承でデフォルトフィールドを持つ基底クラスを設計する際に
必ず発生する問題。`kw_only=True`（Python 3.10+）が最もクリーンな解決策。

## 観察

### O1: `EventBus` は `defaultdict(list)` で型ごとのハンドラーリストを管理できる

```python
class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler[DomainEvent]]] = defaultdict(list)

    def subscribe(self, event_type: type[E], handler: EventHandler[E]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            handler(event)
```

`type(event)` を辞書キーにすることで、イベント型ごとのハンドラー一覧を O(1) で引ける。

### O2: ハンドラー未登録のイベントは安全にスキップされる

`defaultdict` でもキーが存在しない場合は `get()` で空リストが返るため、
ハンドラーが未登録のイベントを publish しても例外が起きない。

## まとめ

FP1（dataclass 継承 + kw_only）を how-to/domain-events.md に追記予定。
インプロセス イベントバスは `defaultdict` + ジェネリックハンドラーで
最小コードで実装でき、テスト時には `EventBus.clear()` でリセットできる。
