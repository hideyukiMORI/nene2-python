# FT88: ドメインイベント — 同期イベントバスパターン検証

**日付**: 2026-05-20  
**テーマ**: FastAPI/nene2 でのドメインイベント実装方法と摩擦点  
**バージョン**: v1.8.30  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft88-domain-events/`

---

## 概要

ドメインイベント（`OrderPlacedEvent`, `OrderCancelledEvent`）を発行し、
通知・監査ログなどのサイドエフェクトを分離するパターンを検証。
シンプルな同期 `EventBus` を自前実装し、nene2 のアーキテクチャと組み合わせた。
nene2 に EventBus の仕組みがないため、ガイダンスの欠如が摩擦ポイントとなる。

---

## 実装パターン

### EventBus（自前実装）

```python
type EventHandler[T] = Callable[[T], None]

class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler[Any]]] = defaultdict(list)
        self.published: list[Any] = []  # テスト用

    def subscribe[T](self, event_type: type[T], handler: EventHandler[T]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: Any) -> None:
        self.published.append(event)
        for handler in self._handlers[type(event)]:
            handler(event)
```

### UseCase でのイベント発行

```python
@app.post("/orders", response_model=OrderResponse, status_code=201)
def place_order(body: PlaceOrderBody) -> JSONResponse:
    order = Order(...)
    _orders[order.order_id] = order

    # ← イベント発行
    event_bus.publish(OrderPlacedEvent(
        order_id=order.order_id,
        customer_id=order.customer_id,
        total=order.total,
    ))
    return JSONResponse({...}, status_code=201)
```

---

## 発見した問題

### 問題1: EventBus が nene2 に含まれていない

nene2 はドメインイベントのアーキテクチャパターンを提供していない。
ユーザーが自前で `EventBus` を実装する必要があり、設計が人によって異なる。
「どのレイヤーでイベントを発行するか」「イベントをどう注入するか」のガイダンスがない。

### 問題2: 同期イベントバスでは例外がHTTPレスポンスに影響する

```python
# イベントハンドラーで例外が発生すると...
def _on_order_placed(event: OrderPlacedEvent) -> None:
    send_email(event)  # ← これが失敗すると

# → ErrorHandlerMiddleware が 500 を返す
# → 注文は作成されたのに 500 でクライアントに返る
```

「注文は DB に保存されたが通知送信に失敗」の場合、
同期バスでは HTTP レスポンスが 500 になってしまう。
`BackgroundTasks` と組み合わせるか、非同期バスを使う必要があるが、
nene2 ドキュメントにそのパターンが示されていない。

### 問題3: TestClient.delete() が json= をサポートしない

```python
# ❌ TypeError: TestClient.delete() got an unexpected keyword argument 'json'
client.delete("/orders/1", json={"reason": "..."})

# ✅ 回避策
client.request("DELETE", "/orders/1", json={"reason": "..."})
```

DELETE + リクエストボディのパターンを httpx の TestClient がサポートしない。
この摩擦は nene2 に起因しないが、DELETE + ボディが必要な API 設計時にハマる。

---

## テスト結果（全14件パス）

```
test_place_order_returns_201                        PASSED
test_place_order_publishes_event                    PASSED
test_place_order_triggers_notification              PASSED
test_place_order_records_audit_log                  PASSED
test_cancel_order_returns_204                       PASSED
test_cancel_order_publishes_event                   PASSED
test_cancel_order_404                               PASSED
test_cancel_order_does_not_publish_event_on_404     PASSED
test_event_bus_subscribe_and_publish                PASSED
test_event_bus_multiple_handlers                    PASSED
test_event_bus_unrelated_handler_not_called         PASSED
test_event_bus_records_published_events             PASSED
test_friction_event_bus_not_part_of_nene2           PASSED
test_friction_event_handler_exception_propagates    PASSED
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F88-1 | EventBus が nene2 に含まれていない、ガイダンスもない | 中 |
| F88-2 | 同期イベントバスではハンドラー例外が HTTP 500 になる、BackgroundTasks との組み合わせガイドがない | 高 |
| F88-3 | TestClient.delete() が json= をサポートしない（httpx の制限） | 低 |

---

## 使用感（主観評価）

### 直感性 ★★★☆☆

EventBus 自体の実装は簡単。Python 3.12 のジェネリクス構文 (`type EventHandler[T]`) で
型安全にハンドラーを登録できる。問題はアーキテクチャの指針がないこと。

### 実害の深刻さ ★★★★☆

F88-2 の「サイドエフェクト失敗で HTTP 500」は実際の運用で問題になる。
メール送信・Slack 通知などの外部連携は失敗しても注文作成は成功扱いにしたい。
`BackgroundTasks` との組み合わせパターンが必要。

### 修正のしやすさ ★★★★☆

- F88-1: ドキュメント（アーキテクチャガイド）を追加するだけ
- F88-2: `BackgroundTasks` とのパターン例を how-to に追加
- F88-3: コードコメント or ドキュメントで `client.request()` を使うよう明記

### 総合コメント

nene2 は「薄い HTTP 層」原則で UseCase とドメインを分離しているため、
EventBus を UseCase に注入するのは自然に実装できる。
ただし、「どこで EventBus を初期化して DI するか」が明確でなく、
グローバル変数 vs lifespan + app.state vs Depends() の選択に迷う。

---

## 推奨アクション

1. **docs**: how-to ガイドに「ドメインイベントパターン」を追加
   - シンプルな同期 EventBus の実装例
   - BackgroundTasks と組み合わせた非同期サイドエフェクトパターン
   - EventBus の DI 方法（lifespan + app.state または module-level singleton）
2. **docs**: DELETE + リクエストボディのテスト方法 (`client.request("DELETE", ...)`) を明記
