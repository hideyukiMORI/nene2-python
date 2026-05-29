# How-to: BackgroundTasks

So führen Sie nach der Antwort Arbeit mit FastAPIs `BackgroundTasks` aus.

---

## 1. Grundlegendes Muster

```python
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

def send_notification(message: str) -> None:
    # langsame Arbeit (E-Mail versenden, externen API-Aufruf tätigen, usw.)
    print(f"Sending: {message}")

@app.post("/orders", status_code=201)
def create_order(
    body: CreateOrderBody,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    order = process_order(body)
    background_tasks.add_task(send_notification, f"Order {order.order_id} created")
    return JSONResponse({"order_id": order.order_id}, status_code=201)
```

---

## 2. Vom UseCase trennen

Um den UseCase HTTP-unabhängig zu halten, übergeben Sie `BackgroundTasks` nicht an ihn. Empfangen Sie das Ereignis in der Handler-Schicht und fügen Sie es dort zu BackgroundTasks hinzu.

```python
# ✅ der UseCase weiß nichts von BackgroundTasks
class CreateOrderUseCase:
    def execute(self, body: CreateOrderInput) -> CreateOrderOutput:
        order = Order(...)
        return CreateOrderOutput(order_id=order.order_id, notify_email=body.email)

# BackgroundTasks in der Handler-Schicht verwenden
@app.post("/orders", status_code=201)
def create_order(
    body: CreateOrderBody,
    background_tasks: BackgroundTasks,
    use_case: CreateOrderUseCase = Depends(get_use_case),
) -> JSONResponse:
    result = use_case.execute(CreateOrderInput(email=body.email))
    background_tasks.add_task(send_notification, result.notify_email)
    return JSONResponse({"order_id": result.order_id}, status_code=201)
```

---

## 3. Verhalten unter TestClient

Unter `TestClient` läuft `BackgroundTasks` synchron **bevor** die Antwort zurückgegeben wird.

```python
executed: list[str] = []

def track_task(msg: str) -> None:
    executed.append(msg)

# in Tests läuft BackgroundTasks synchron
r = client.post("/orders", json={"email": "alice@example.com"})
assert r.status_code == 201
assert len(executed) == 1  # bereits ausgeführt
```

In der Produktion läuft es asynchron (nach der Antwort); beachten Sie, dass es in Tests synchron läuft.

---

## 4. Ein Fehler verursacht keinen 500-Fehler

Wenn innerhalb eines `BackgroundTasks`-Tasks eine Ausnahme ausgelöst wird, wurde die Antwort bereits gesendet, daher wird sie kein 500 mehr. Der Fehler wird protokolliert.

```python
def risky_task() -> None:
    raise RuntimeError("Background task failed")

# die Antwort gibt 201 zurück (der Hintergrundfehler ist verborgen)
background_tasks.add_task(risky_task)
```

Für wichtige Arbeit verlassen Sie sich nicht auf BackgroundTasks — verwenden Sie eine Job-Queue (Celery, ARQ, usw.).

---

## 5. Kombination mit async def

`background_tasks.add_task()` akzeptiert sowohl synchrone als auch asynchrone Funktionen.

```python
async def async_notification(email: str) -> None:
    await send_email_async(email)

background_tasks.add_task(async_notification, user.email)
```
