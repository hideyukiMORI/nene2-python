# 操作指南：结构化日志（structlog）

如何使用 `nene2.log` 和 `RequestLoggingMiddleware` 配置 structlog，以及传播请求上下文的模式。

---

## 1. 在应用启动时配置日志

在 `create_app()` 顶部调用 `setup_logging()`。

```python
from nene2.log import setup_logging
from nene2.middleware import RequestIdMiddleware, RequestLoggingMiddleware

setup_logging(app_env="production", log_level="INFO")

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)
```

`app_env="local"` 时输出彩色控制台日志；否则输出 JSON 日志。

---

## 2. 在 endpoint 中输出日志

```python
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

@app.post("/orders")
def create_order(body: OrderRequest) -> JSONResponse:
    logger.info("order.creating", item_id=body.item_id)
    # request_id、method、path 由 RequestLoggingMiddleware 自动添加
    ...
```

`RequestLoggingMiddleware` 在请求开始时通过 `structlog.contextvars.bind_contextvars()` 绑定 `request_id`、`method` 和 `path`，因此 endpoint 内的每条日志都会自动携带这些字段。

---

## 3. 在 pytest 中捕获 structlog 日志

在测试文件顶部或 `conftest.py` 中调用 `configure_for_testing()`。

```python
from nene2.log import configure_for_testing

configure_for_testing()  # 将 structlog 路由到标准库日志桥接器

def test_order_logs(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    with caplog.at_level(logging.INFO):
        client.post("/orders", json={"item_id": 1, "quantity": 1})
    assert any("order.creating" in r.message for r in caplog.records)
```

---

## 4. X-Request-Id 仅以 UUID v4 形式转发

`RequestIdMiddleware` 只接受 UUID v4 格式的客户端提供的 `X-Request-Id`。非 UUID 值（如 `"test-id-001"`）会被静默替换为新生成的 UUID。

```python
# ❌ 非 UUID 格式 → 生成新的 UUID
headers = {"X-Request-Id": "test-req-001"}

# ✅ UUID v4 格式 → 原样转发
headers = {"X-Request-Id": "550e8400-e29b-41d4-a716-446655440000"}
```

在测试中固定请求 ID，请使用 `uuid.uuid4()` 生成，或使用固定的 UUID v4 字符串（第三组以 `4xxx` 开头，第四组以 `[89ab]xxx` 开头）。此设计是为了防范日志注入攻击。
