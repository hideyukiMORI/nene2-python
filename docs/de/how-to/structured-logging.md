# How-to: Strukturiertes Logging (structlog)

So konfigurieren Sie structlog mit `nene2.log` und `RequestLoggingMiddleware` sowie das Muster zur Weitergabe des Request-Kontexts.

---

## 1. Logging beim App-Start konfigurieren

Rufen Sie `setup_logging()` am Anfang von `create_app()` auf.

```python
from nene2.log import setup_logging
from nene2.middleware import RequestIdMiddleware, RequestLoggingMiddleware

setup_logging(app_env="production", log_level="INFO")

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)
```

Mit `app_env="local"` erhalten Sie farbige Konsolenausgabe; andernfalls JSON-Logs.

---

## 2. Logs innerhalb eines Endpunkts ausgeben

```python
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

@app.post("/orders")
def create_order(body: OrderRequest) -> JSONResponse:
    logger.info("order.creating", item_id=body.item_id)
    # request_id, method, path werden automatisch von RequestLoggingMiddleware hinzugefügt
    ...
```

`RequestLoggingMiddleware` bindet `request_id`, `method` und `path` am Anfang der Anfrage über `structlog.contextvars.bind_contextvars()`, sodass jedes Log innerhalb des Endpunkts diese automatisch trägt.

---

## 3. structlog-Logs in pytest erfassen

Rufen Sie `configure_for_testing()` am Anfang der Testdatei oder `conftest.py` auf.

```python
from nene2.log import configure_for_testing

configure_for_testing()  # structlog durch die stdlib-Logging-Brücke leiten

def test_order_logs(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    with caplog.at_level(logging.INFO):
        client.post("/orders", json={"item_id": 1, "quantity": 1})
    assert any("order.creating" in r.message for r in caplog.records)
```

---

## 4. X-Request-Id wird nur in UUID-v4-Form weitergegeben

`RequestIdMiddleware` akzeptiert eine vom Client bereitgestellte `X-Request-Id` nur in UUID-v4-Form. Ein Nicht-UUID-Wert (wie `"test-id-001"`) wird stillschweigend durch eine neue UUID ersetzt.

```python
# ❌ Nicht-UUID-Form → eine neue UUID wird generiert
headers = {"X-Request-Id": "test-req-001"}

# ✅ UUID-v4-Form → wird so weitergegeben wie sie ist
headers = {"X-Request-Id": "550e8400-e29b-41d4-a716-446655440000"}
```

Um eine Request-ID in Tests zu fixieren, generieren Sie eine mit `uuid.uuid4()` oder verwenden Sie einen festen UUID-v4-String (dritte Gruppe `4xxx`, vierte Gruppe `[89ab]xxx`). Dieses Design ist beabsichtigt als Schutz vor Log-Injection.
