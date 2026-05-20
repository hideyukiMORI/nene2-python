# How-to: 構造化ログ（structlog）

`nene2.log` と `RequestLoggingMiddleware` を使った structlog の設定と、
リクエストコンテキストの伝播パターンを説明する。

---

## 1. アプリ起動時にログを設定する

`setup_logging()` を `create_app()` の先頭で呼ぶ。

```python
from nene2.log import setup_logging
from nene2.middleware import RequestIdMiddleware, RequestLoggingMiddleware

setup_logging(app_env="production", log_level="INFO")

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)
```

`app_env="local"` のときは色付きコンソール出力、それ以外は JSON ログになる。

---

## 2. エンドポイント内でログを発行する

```python
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

@app.post("/orders")
def create_order(body: OrderRequest) -> JSONResponse:
    logger.info("order.creating", item_id=body.item_id)
    # request_id, method, path は RequestLoggingMiddleware が自動付与
    ...
```

`RequestLoggingMiddleware` がリクエスト開始時に `request_id`, `method`, `path` を
`structlog.contextvars.bind_contextvars()` でバインドするため、
エンドポイント内の全ログにこれらが自動付与される。

---

## 3. pytest で structlog ログをキャプチャする

`configure_for_testing()` を test ファイルまたは `conftest.py` の先頭で呼ぶ。

```python
from nene2.log import configure_for_testing

configure_for_testing()  # structlog を stdlib logging ブリッジ経由に切り替え

def test_order_logs(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    with caplog.at_level(logging.INFO):
        client.post("/orders", json={"item_id": 1, "quantity": 1})
    assert any("order.creating" in r.message for r in caplog.records)
```

---

## 4. X-Request-Id は UUID v4 形式のみ転送される

`RequestIdMiddleware` はクライアント提供の `X-Request-Id` を UUID v4 形式のみ受け付ける。
非 UUID 値（`"test-id-001"` など）は黙って新規 UUID に置き換えられる。

```python
# ❌ 非 UUID 形式 → 新規 UUID が生成される
headers = {"X-Request-Id": "test-req-001"}

# ✅ UUID v4 形式 → そのまま転送される
headers = {"X-Request-Id": "550e8400-e29b-41d4-a716-446655440000"}
```

テストでリクエスト ID を固定したい場合は `uuid.uuid4()` で生成するか、
固定の UUID v4 文字列（第 3 グループが `4xxx`、第 4 グループが `[89ab]xxx`）を使う。
この設計はログインジェクション対策のために意図的に行われている。
