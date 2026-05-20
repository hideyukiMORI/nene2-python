# Field Trial 115: structlog 構造化ログ + リクエストコンテキスト伝播

## テーマ

`RequestLoggingMiddleware` + `RequestIdMiddleware` が structlog contextvars に自動バインドする `request_id` を、
エンドポイント内のログ呼び出しに透過的に伝播させるパターンを検証する。
また pytest の `caplog` フィクスチャで structlog 出力をキャプチャできるかを確認する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft115-structured-logging/` に以下を実装:

- `RequestLoggingMiddleware` + `RequestIdMiddleware` を組み合わせたアプリ
- `structlog.get_logger(__name__)` でエンドポイント内からログを発行
- `get_request_id()` でリクエスト ID をレスポンスボディに含める
- `configure_for_testing()` を呼んで pytest caplog と統合
- 11 テスト通過（修正後）

## テスト結果

2 件修正後、全 11 テスト通過。

## Friction Points

### FP1: `X-Request-Id` は UUID v4 形式のみ転送される — 非 UUID 値は黙って置換される

**状況**: テストで `X-Request-Id: test-req-001` を送信したところ、レスポンスに別の UUID が返ってきた。
`RequestIdMiddleware` は UUID v4 形式のみ受け付け、それ以外は新規 UUID を生成する設計になっている。

```python
# ❌ 非 UUID 形式は無効化される
client.post("/orders", headers={"X-Request-Id": "test-req-001"})
# → レスポンスの X-Request-Id は新規生成 UUID になる

# ✅ UUID v4 形式なら転送される
valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
client.post("/orders", headers={"X-Request-Id": valid_uuid})
# → レスポンスの X-Request-Id は "550e8400-e29b-41d4-a716-446655440000"
```

**影響**: 小。設計として正しい動作（ログインジェクション対策）だが、
テストで任意文字列を X-Request-Id に指定しようとすると予期せず失敗する。

**代替案**: UUID v4 形式のリクエスト ID を使うか、`uuid.uuid4()` で生成してからテスト内で指定する。

## 観察

### O1: `RequestLoggingMiddleware` が structlog contextvars に request_id を自動バインド

```python
structlog.contextvars.bind_contextvars(
    request_id=request_id_var.get(),
    method=request.method,
    path=request.url.path,
)
```

エンドポイント内で `logger.info("order.creating", item_id=body.item_id)` を呼ぶと、
`request_id`, `method`, `path` が自動付与される。明示的な引数渡しは不要。

### O2: `configure_for_testing()` で structlog を pytest caplog に接続できる

```python
# conftest.py または test ファイルの先頭
from nene2.log import configure_for_testing
configure_for_testing()

def test_logs(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        client.post("/orders", json={"item_id": 2, "quantity": 5})
    assert any("order.creating" in record.message for record in caplog.records)
```

`configure_for_testing()` は structlog を stdlib logging ブリッジ経由で出力するように設定し直す。
これにより pytest の caplog フィクスチャが structlog の出力を記録できる。

### O3: `WARNING` レベルのログも caplog で確認できる

```python
with caplog.at_level(logging.WARNING):
    client.get("/orders/404")
assert any("order.not_found" in record.message for record in caplog.records)
```

`logger.warning(...)` は caplog の `WARNING` レベルフィルターで確認できる。

## まとめ

FP1（UUID v4 バリデーション）を how-to に追記予定。
structlog + contextvars の伝播はフレームワークが完全に自動化しており、
エンドポイント側の実装は `structlog.get_logger(__name__)` の呼び出しのみで完結する。
