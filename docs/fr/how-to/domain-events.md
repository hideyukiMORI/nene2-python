# Guide pratique : schémas d'événements de domaine

Un schéma pour séparer les effets de bord après l'exécution d'un UseCase (envoi d'email,
journalisation, notifications) en utilisant des événements de domaine et BackgroundTasks.

---

## 1. Schéma de base : exécuter des événements de façon asynchrone avec BackgroundTasks

Exécutez du travail après la réponse avec les `BackgroundTasks` de FastAPI.

```python
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

def send_welcome_email(email: str) -> None:
    # envoi d'email (lent)
    ...

@app.post("/users", status_code=201)
def create_user(body: CreateUserBody, background_tasks: BackgroundTasks) -> JSONResponse:
    user = create_user_use_case(body.name, body.email)
    background_tasks.add_task(send_welcome_email, user.email)
    return JSONResponse({"user_id": user.user_id}, status_code=201)
```

---

## 2. Schéma EventBus : publier des événements de domaine depuis le UseCase

Un schéma où le UseCase publie des événements et des handlers s'abonnent. Le UseCase
n'a aucune connaissance HTTP (pas de BackgroundTasks).

```python
from dataclasses import dataclass
from typing import Any, Callable

# définition de l'événement
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

# UseCase : indépendant de HTTP
class CreateUserUseCase:
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    def execute(self, name: str, email: str) -> User:
        user = User(...)
        self._event_bus.publish(UserCreatedEvent(user.user_id, user.email))
        return user

# enregistrer le handler
def on_user_created(event: UserCreatedEvent) -> None:
    send_welcome_email(event.email)

event_bus.subscribe(UserCreatedEvent, on_user_created)
```

---

## 3. Combiner BackgroundTasks et EventBus

Utilisez BackgroundTasks dans le handler HTTP pour exécuter les handlers de l'EventBus
en arrière-plan.

```python
@app.post("/users", status_code=201)
def create_user(
    body: CreateUserBody,
    background_tasks: BackgroundTasks,
    use_case: CreateUserUseCase = Depends(get_create_user_use_case),
) -> JSONResponse:
    # le UseCase publie l'événement de façon synchrone (le met en file sur l'EventBus)
    user = use_case.execute(body.name, body.email)
    # exécuter les handlers d'événements après la réponse via BackgroundTasks
    for handler_call in collected_events:
        background_tasks.add_task(handler_call)
    return JSONResponse({"user_id": user.user_id}, status_code=201)
```

---

## 4. Vérifier les événements dans les tests

Dans les tests, la complétion n'attend pas BackgroundTasks — sous TestClient, il s'exécute
de façon synchrone et immédiate.

```python
# sous TestClient, BackgroundTasks s'exécute de façon synchrone avant que la réponse ne soit retournée
executed = []
event_bus.subscribe(UserCreatedEvent, lambda e: executed.append(e))

with TestClient(app) as client:
    r = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})

assert len(executed) == 1  # BackgroundTasks déjà terminé
assert executed[0].email == "alice@example.com"
```

---

## Mises en garde

- `EventBus` tend à devenir une variable globale au niveau du module. Si des handlers s'accumulent
  à travers les tests, réinitialisez-le avec une fixture `autouse`.
- Lors de la publication d'événements dans un UseCase, passez `EventBus` comme argument de
  constructeur (injection de constructeur) — évitez une référence globale.

---

## 5. Héritage de dataclass : champs requis après champs avec valeur par défaut

Si une classe de base a un champ `default_factory`, ajouter un champ requis dans une sous-classe
échoue selon les règles Python pour les dataclasses. `kw_only=True` (Python 3.10+) résout le problème.

```python
# ❌ erreur : 'order_id' est un champ requis venant après 'occurred_at'
@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str  # TypeError: non-default argument follows default argument

# ✅ résolu avec kw_only=True (Python 3.10+)
@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC), kw_only=True)

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str  # OK — les champs kw_only ne sont pas soumis à la contrainte d'ordre MRO
    total_amount: int
```

Avec `kw_only=True`, le champ devient keyword-only dans `__init__`. Les arguments requis d'une
sous-classe peuvent être définis comme arguments positionnels ordinaires, et `occurred_at` est
traité comme optionnel.
