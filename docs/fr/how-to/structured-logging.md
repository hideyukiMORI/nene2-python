# Guide pratique : journalisation structurée (structlog)

Comment configurer structlog avec `nene2.log` et `RequestLoggingMiddleware`, et le schéma
pour propaguer le contexte de requête.

---

## 1. Configurer la journalisation au démarrage de l'application

Appelez `setup_logging()` en haut de `create_app()`.

```python
from nene2.log import setup_logging
from nene2.middleware import RequestIdMiddleware, RequestLoggingMiddleware

setup_logging(app_env="production", log_level="INFO")

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)
```

Avec `app_env="local"` vous obtenez une sortie console colorée ; sinon des logs JSON.

---

## 2. Émettre des logs dans un endpoint

```python
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

@app.post("/orders")
def create_order(body: OrderRequest) -> JSONResponse:
    logger.info("order.creating", item_id=body.item_id)
    # request_id, method, path sont ajoutés automatiquement par RequestLoggingMiddleware
    ...
```

`RequestLoggingMiddleware` lie `request_id`, `method` et `path` au début de la requête via
`structlog.contextvars.bind_contextvars()`, de sorte que chaque log dans l'endpoint les porte
automatiquement.

---

## 3. Capturer les logs structlog dans pytest

Appelez `configure_for_testing()` en haut du fichier de test ou dans `conftest.py`.

```python
from nene2.log import configure_for_testing

configure_for_testing()  # router structlog via le pont de journalisation stdlib

def test_order_logs(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    with caplog.at_level(logging.INFO):
        client.post("/orders", json={"item_id": 1, "quantity": 1})
    assert any("order.creating" in r.message for r in caplog.records)
```

---

## 4. X-Request-Id n'est transmis qu'en forme UUID v4

`RequestIdMiddleware` n'accepte un `X-Request-Id` fourni par le client qu'en forme UUID v4.
Une valeur non-UUID (comme `"test-id-001"`) est silencieusement remplacée par un nouveau UUID.

```python
# ❌ forme non-UUID → un nouveau UUID est généré
headers = {"X-Request-Id": "test-req-001"}

# ✅ forme UUID v4 → transmis tel quel
headers = {"X-Request-Id": "550e8400-e29b-41d4-a716-446655440000"}
```

Pour épingler un request ID dans les tests, générez-en un avec `uuid.uuid4()` ou utilisez
une chaîne UUID v4 fixe (troisième groupe `4xxx`, quatrième groupe `[89ab]xxx`). Cette conception
est intentionnelle, comme défense contre l'injection de logs.
