# Como fazer: padrões de eventos de domínio

Um padrão para separar efeitos colaterais após um UseCase executar (enviar email,
logging, notificações) usando eventos de domínio e BackgroundTasks.

---

## 1. Padrão básico: executar eventos de forma assíncrona com BackgroundTasks

Execute trabalho após a resposta com o `BackgroundTasks` do FastAPI.

```python
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

def send_welcome_email(email: str) -> None:
    # envio de email (lento)
    ...

@app.post("/users", status_code=201)
def create_user(body: CreateUserBody, background_tasks: BackgroundTasks) -> JSONResponse:
    user = create_user_use_case(body.name, body.email)
    background_tasks.add_task(send_welcome_email, user.email)
    return JSONResponse({"user_id": user.user_id}, status_code=201)
```

---

## 2. Padrão EventBus: publicar eventos de domínio a partir do UseCase

Um padrão onde o UseCase publica eventos e handlers assinam. O UseCase
não tem conhecimento de HTTP (sem BackgroundTasks).

```python
from dataclasses import dataclass
from typing import Any, Callable

# definição do evento
@dataclass(frozen=True, slots=True)
class UserCreatedEvent:
    user_id: int
    email: str

# EventBus
type EventHandler = Callable[[Any], None]

class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = {}

    def subscribe(self, event_type: type, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: object) -> None:
        for handler in self._handlers.get(type(event), []):
            handler(event)

event_bus = EventBus()

# UseCase: independente de HTTP
class CreateUserUseCase:
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    def execute(self, name: str, email: str) -> User:
        user = User(...)
        self._event_bus.publish(UserCreatedEvent(user.user_id, user.email))
        return user

# registrar handler
def on_user_created(event: UserCreatedEvent) -> None:
    send_welcome_email(event.email)

event_bus.subscribe(UserCreatedEvent, on_user_created)
```

---

## 3. Combinando BackgroundTasks e EventBus

Use BackgroundTasks no handler HTTP para executar os handlers do EventBus em
background.

```python
@app.post("/users", status_code=201)
def create_user(
    body: CreateUserBody,
    background_tasks: BackgroundTasks,
    use_case: CreateUserUseCase = Depends(get_create_user_use_case),
) -> JSONResponse:
    # o UseCase publica o evento de forma síncrona (enfileira no EventBus)
    user = use_case.execute(body.name, body.email)
    # execute os handlers de evento após a resposta via BackgroundTasks
    for handler_call in collected_events:
        background_tasks.add_task(handler_call)
    return JSONResponse({"user_id": user.user_id}, status_code=201)
```

---

## 4. Verificando eventos nos testes

Nos testes, a conclusão não espera o BackgroundTasks — no TestClient ele executa
de forma síncrona e imediatamente.

```python
# no TestClient, BackgroundTasks executa de forma síncrona antes de a resposta retornar
executed = []
event_bus.subscribe(UserCreatedEvent, lambda e: executed.append(e))

with TestClient(app) as client:
    r = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})

assert len(executed) == 1  # BackgroundTasks já concluiu
assert executed[0].email == "alice@example.com"
```

---

## Ressalvas

- `EventBus` tende a se tornar um global de nível de módulo. Se handlers se acumulam entre
  testes, reinicie-o com um fixture `autouse`.
- Ao publicar eventos dentro de um UseCase, passe `EventBus` como argumento do construtor
  (injeção por construtor) — evite uma referência global.

---

## 5. Herança de dataclass: campos obrigatórios após campos com padrão

Se uma classe base tem um campo `default_factory`, adicionar um campo obrigatório em uma
subclasse gera erro sob as regras de dataclass do Python. `kw_only=True` (Python 3.10+)
resolve isso.

```python
# ❌ erro: 'order_id' é um campo obrigatório vindo após 'occurred_at'
@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str  # TypeError: non-default argument follows default argument

# ✅ resolvido com kw_only=True (Python 3.10+)
@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC), kw_only=True)

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str  # OK — campos kw_only não estão sujeitos à restrição de ordenação MRO
    total_amount: int
```

Com `kw_only=True`, o campo se torna keyword-only em `__init__`. Os argumentos obrigatórios
de uma subclasse podem ser definidos como argumentos posicionais comuns, e
`occurred_at` é tratado como opcional.
