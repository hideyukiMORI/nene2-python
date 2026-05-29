# Como fazer: logging estruturado (structlog)

Como configurar o structlog com `nene2.log` e `RequestLoggingMiddleware`, e
o padrão para propagação de contexto de requisição.

---

## 1. Configurar logging na inicialização do app

Chame `setup_logging()` no topo de `create_app()`.

```python
from nene2.log import setup_logging
from nene2.middleware import RequestIdMiddleware, RequestLoggingMiddleware

setup_logging(app_env="production", log_level="INFO")

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)
```

Com `app_env="local"` você recebe saída colorida no console; caso contrário, logs JSON.

---

## 2. Emitir logs dentro de um endpoint

```python
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

@app.post("/orders")
def create_order(body: OrderRequest) -> JSONResponse:
    logger.info("order.creating", item_id=body.item_id)
    # request_id, method, path são adicionados automaticamente pelo RequestLoggingMiddleware
    ...
```

`RequestLoggingMiddleware` vincula `request_id`, `method` e `path` no início
da requisição via `structlog.contextvars.bind_contextvars()`, então todo log dentro do
endpoint os carrega automaticamente.

---

## 3. Capturar logs do structlog no pytest

Chame `configure_for_testing()` no topo do arquivo de teste ou em `conftest.py`.

```python
from nene2.log import configure_for_testing

configure_for_testing()  # rotear structlog pelo bridge de logging da stdlib

def test_order_logs(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    with caplog.at_level(logging.INFO):
        client.post("/orders", json={"item_id": 1, "quantity": 1})
    assert any("order.creating" in r.message for r in caplog.records)
```

---

## 4. X-Request-Id só é encaminhado na forma UUID v4

`RequestIdMiddleware` só aceita um `X-Request-Id` fornecido pelo cliente na forma UUID v4.
Um valor não-UUID (como `"test-id-001"`) é silenciosamente substituído por um novo UUID.

```python
# ❌ forma não-UUID → um novo UUID é gerado
headers = {"X-Request-Id": "test-req-001"}

# ✅ forma UUID v4 → encaminhado como está
headers = {"X-Request-Id": "550e8400-e29b-41d4-a716-446655440000"}
```

Para fixar um request ID nos testes, gere um com `uuid.uuid4()` ou use uma string
UUID v4 fixa (terceiro grupo `4xxx`, quarto grupo `[89ab]xxx`). Esse design é
intencional, como defesa contra log injection.
