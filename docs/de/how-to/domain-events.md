# How-to: Domain-Event-Muster

Ein Muster zur Trennung von Nebeneffekten nach dem Ausführen eines UseCase (E-Mail versenden, Logging, Benachrichtigungen) mit Domain-Events und BackgroundTasks.

---

## 1. Grundlegendes Muster: Events asynchron mit BackgroundTasks ausführen

Führen Sie Arbeit nach der Antwort mit FastAPIs `BackgroundTasks` aus.

```python
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

def send_welcome_email(email: str) -> None:
    # E-Mail versenden (langsam)
    ...

@app.post("/users", status_code=201)
def create_user(body: CreateUserBody, background_tasks: BackgroundTasks) -> JSONResponse:
    user = create_user_use_case(body.name, body.email)
    background_tasks.add_task(send_welcome_email, user.email)
    return JSONResponse({"user_id": user.user_id}, status_code=201)
```

---

## 2. EventBus-Muster: Domain-Events aus dem UseCase veröffentlichen

Ein Muster, bei dem der UseCase Events veröffentlicht und Handler sich abonnieren. Der UseCase hat kein HTTP-Wissen (keine BackgroundTasks).

```python
from dataclasses import dataclass
from typing import Any, Callable

# Event-Definition
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

# UseCase: HTTP-unabhängig
class CreateUserUseCase:
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    def execute(self, name: str, email: str) -> User:
        user = User(...)
        self._event_bus.publish(UserCreatedEvent(user.user_id, user.email))
        return user

# Handler registrieren
def on_user_created(event: UserCreatedEvent) -> None:
    send_welcome_email(event.email)

event_bus.subscribe(UserCreatedEvent, on_user_created)
```

---

## 3. BackgroundTasks und EventBus kombinieren

Verwenden Sie BackgroundTasks im HTTP-Handler, um die EventBus-Handler im Hintergrund auszuführen.

```python
@app.post("/users", status_code=201)
def create_user(
    body: CreateUserBody,
    background_tasks: BackgroundTasks,
    use_case: CreateUserUseCase = Depends(get_create_user_use_case),
) -> JSONResponse:
    # Der UseCase veröffentlicht das Event synchron (stellt es in den EventBus)
    user = use_case.execute(body.name, body.email)
    # Event-Handler nach der Antwort über BackgroundTasks ausführen
    for handler_call in collected_events:
        background_tasks.add_task(handler_call)
    return JSONResponse({"user_id": user.user_id}, status_code=201)
```

---

## 4. Events in Tests verifizieren

In Tests wartet der Abschluss nicht auf BackgroundTasks — unter TestClient läuft es synchron und sofort.

```python
# unter TestClient läuft BackgroundTasks synchron, bevor die Antwort zurückkommt
executed = []
event_bus.subscribe(UserCreatedEvent, lambda e: executed.append(e))

with TestClient(app) as client:
    r = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})

assert len(executed) == 1  # BackgroundTasks bereits abgeschlossen
assert executed[0].email == "alice@example.com"
```

---

## Vorbehalte

- `EventBus` neigt dazu, eine modulweite globale Variable zu werden. Wenn sich Handler über Tests ansammeln, setzen Sie ihn mit einem `autouse`-Fixture zurück.
- Beim Veröffentlichen von Events innerhalb eines UseCase übergeben Sie `EventBus` als Konstruktor-Argument (Constructor Injection) — vermeiden Sie eine globale Referenz.

---

## 5. Dataclass-Vererbung: Pflichtfelder nach Feldern mit Standardwerten

Wenn eine Basisklasse ein `default_factory`-Feld hat, führt das Hinzufügen eines Pflichtfelds in einer Unterklasse zu einem Fehler gemäß Pythons Dataclass-Regeln. `kw_only=True` (Python 3.10+) löst dies.

```python
# ❌ Fehler: 'order_id' ist ein Pflichtfeld nach 'occurred_at'
@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str  # TypeError: non-default argument follows default argument

# ✅ mit kw_only=True (Python 3.10+) gelöst
@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC), kw_only=True)

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str  # OK — kw_only-Felder unterliegen nicht der MRO-Reihenfolgeschränkung
    total_amount: int
```

Mit `kw_only=True` wird das Feld in `__init__` zu einem Keyword-Only-Argument. Pflichtargumente einer Unterklasse können als normale Positionsargumente definiert werden, und `occurred_at` wird als optional behandelt.
