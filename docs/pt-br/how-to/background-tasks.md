# Como fazer: BackgroundTasks

Como executar trabalho após a resposta usando o `BackgroundTasks` do FastAPI.

---

## 1. Padrão básico

```python
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

def send_notification(message: str) -> None:
    # trabalho lento (enviar email, chamar API externa, etc.)
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

## 2. Mantendo separado do UseCase

Para manter o UseCase independente de HTTP, não passe `BackgroundTasks` para dentro dele.
Receba o evento na camada do handler e adicione ao BackgroundTasks lá.

```python
# ✅ o UseCase não sabe sobre BackgroundTasks
class CreateOrderUseCase:
    def execute(self, body: CreateOrderInput) -> CreateOrderOutput:
        order = Order(...)
        return CreateOrderOutput(order_id=order.order_id, notify_email=body.email)

# use BackgroundTasks na camada do handler
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

## 3. Comportamento no TestClient

No `TestClient`, o `BackgroundTasks` executa de forma síncrona **antes** de a resposta
ser retornada.

```python
executed: list[str] = []

def track_task(msg: str) -> None:
    executed.append(msg)

# nos testes, BackgroundTasks executa de forma síncrona
r = client.post("/orders", json={"email": "alice@example.com"})
assert r.status_code == 201
assert len(executed) == 1  # já executado
```

Em produção ele executa de forma assíncrona (após a resposta); note que executa
de forma síncrona nos testes.

---

## 4. Uma falha não gera um 500

Se uma exceção for lançada dentro de uma tarefa do `BackgroundTasks`, a resposta já
foi enviada, então não vira um 500. O erro é registrado em log.

```python
def risky_task() -> None:
    raise RuntimeError("Background task failed")

# a resposta retorna 201 (o erro em background fica oculto)
background_tasks.add_task(risky_task)
```

Para trabalho importante, não dependa do BackgroundTasks — use uma fila de jobs (Celery, ARQ, etc.).

---

## 5. Combinando com async def

`background_tasks.add_task()` aceita tanto funções síncronas quanto assíncronas.

```python
async def async_notification(email: str) -> None:
    await send_email_async(email)

background_tasks.add_task(async_notification, user.email)
```
