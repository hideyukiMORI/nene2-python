# Guide pratique : BackgroundTasks

Comment exécuter du travail après la réponse avec les `BackgroundTasks` de FastAPI.

---

## 1. Schéma de base

```python
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

def send_notification(message: str) -> None:
    # travail lent (envoi d'email, appel d'une API externe, etc.)
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

## 2. Garder la séparation avec le UseCase

Pour maintenir l'indépendance HTTP du UseCase, ne passez pas `BackgroundTasks` dedans.
Recevez l'événement dans la couche handler et ajoutez-le aux BackgroundTasks là.

```python
# ✅ le UseCase ne sait pas que BackgroundTasks existe
class CreateOrderUseCase:
    def execute(self, body: CreateOrderInput) -> CreateOrderOutput:
        order = Order(...)
        return CreateOrderOutput(order_id=order.order_id, notify_email=body.email)

# utiliser BackgroundTasks dans la couche handler
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

## 3. Comportement sous TestClient

Sous `TestClient`, `BackgroundTasks` s'exécute de manière synchrone **avant** que la réponse
soit retournée.

```python
executed: list[str] = []

def track_task(msg: str) -> None:
    executed.append(msg)

# dans les tests, BackgroundTasks s'exécute de façon synchrone
r = client.post("/orders", json={"email": "alice@example.com"})
assert r.status_code == 201
assert len(executed) == 1  # déjà exécuté
```

En production, il s'exécute de façon asynchrone (après la réponse) ; notez qu'il s'exécute
de façon synchrone dans les tests.

---

## 4. Un échec ne provoque pas de 500

Si une exception est levée dans une tâche `BackgroundTasks`, la réponse a déjà été envoyée,
donc elle ne devient pas un 500. L'erreur est journalisée.

```python
def risky_task() -> None:
    raise RuntimeError("Background task failed")

# la réponse retourne 201 (l'erreur de la tâche est masquée)
background_tasks.add_task(risky_task)
```

Pour du travail important, ne comptez pas sur BackgroundTasks — utilisez une file de jobs (Celery, ARQ, etc.).

---

## 5. Combinaison avec async def

`background_tasks.add_task()` accepte les fonctions synchrones et asynchrones.

```python
async def async_notification(email: str) -> None:
    await send_email_async(email)

background_tasks.add_task(async_notification, user.email)
```
