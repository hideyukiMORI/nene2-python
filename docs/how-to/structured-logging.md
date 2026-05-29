# How-to: structured logging (structlog)

How to configure structlog with `nene2.log` and `RequestLoggingMiddleware`, and
the pattern for propagating request context.

---

## 1. Configure logging at app startup

Call `setup_logging()` at the top of `create_app()`.

```python
from nene2.log import setup_logging
from nene2.middleware import RequestIdMiddleware, RequestLoggingMiddleware

setup_logging(app_env="production", log_level="INFO")

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)
```

With `app_env="local"` you get colored console output; otherwise JSON logs.

---

## 2. Emit logs inside an endpoint

```python
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

@app.post("/orders")
def create_order(body: OrderRequest) -> JSONResponse:
    logger.info("order.creating", item_id=body.item_id)
    # request_id, method, path are added automatically by RequestLoggingMiddleware
    ...
```

`RequestLoggingMiddleware` binds `request_id`, `method`, and `path` at the start
of the request via `structlog.contextvars.bind_contextvars()`, so every log inside
the endpoint carries them automatically.

---

## 3. Capture structlog logs in pytest

Call `configure_for_testing()` at the top of the test file or `conftest.py`.

```python
from nene2.log import configure_for_testing

configure_for_testing()  # route structlog through the stdlib logging bridge

def test_order_logs(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    with caplog.at_level(logging.INFO):
        client.post("/orders", json={"item_id": 1, "quantity": 1})
    assert any("order.creating" in r.message for r in caplog.records)
```

---

## 4. X-Request-Id is only forwarded in UUID v4 form

`RequestIdMiddleware` only accepts a client-supplied `X-Request-Id` in UUID v4
form. A non-UUID value (such as `"test-id-001"`) is silently replaced with a new
UUID.

```python
# ❌ non-UUID form → a new UUID is generated
headers = {"X-Request-Id": "test-req-001"}

# ✅ UUID v4 form → forwarded as-is
headers = {"X-Request-Id": "550e8400-e29b-41d4-a716-446655440000"}
```

To pin a request ID in tests, generate one with `uuid.uuid4()` or use a fixed
UUID v4 string (third group `4xxx`, fourth group `[89ab]xxx`). This design is
intentional, as a defense against log injection.
