# Guide pratique : intégrer AsyncUseCase avec FastAPI

## Implémentation basique de AsyncUseCaseProtocol

`AsyncUseCaseProtocol` est un Protocol (typage structurel), donc aucun héritage n'est
nécessaire. Il suffit d'implémenter `async def execute(self, input_: I) -> O` pour être conforme.

```python
from dataclasses import dataclass
from nene2.use_case import AsyncUseCaseProtocol


@dataclass(frozen=True, slots=True)
class FetchUserInput:
    user_id: int


@dataclass(frozen=True, slots=True)
class FetchUserOutput:
    user_id: int
    name: str


class FetchUserUseCase:
    async def execute(self, input_: FetchUserInput) -> FetchUserOutput:
        # travail async : appel API externe ou accès DB
        return FetchUserOutput(user_id=input_.user_id, name="Alice")
```

---

## Intégration avec FastAPI Depends

Passer une fonction factory à `Depends()` est le schéma standard.

```python
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


def get_fetch_user_use_case() -> FetchUserUseCase:
    return FetchUserUseCase()


@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    use_case: FetchUserUseCase = Depends(get_fetch_user_use_case),
) -> JSONResponse:
    result = await use_case.execute(FetchUserInput(user_id=user_id))
    return JSONResponse({"user_id": result.user_id, "name": result.name})
```

---

## DI pour un UseCase avec des dépendances externes

Un UseCase qui prend un repository ou un client externe reçoit ces dépendances injectées via
Depends également.

```python
class FetchUserUseCase:
    def __init__(self, repository: UserRepositoryInterface) -> None:
        self._repository = repository

    async def execute(self, input_: FetchUserInput) -> FetchUserOutput:
        user = await self._repository.find_by_id(input_.user_id)
        return FetchUserOutput(user_id=user.id, name=user.name)


def get_user_repository() -> UserRepositoryInterface:
    return InMemoryUserRepository()


def get_fetch_user_use_case(
    repository: UserRepositoryInterface = Depends(get_user_repository),
) -> FetchUserUseCase:
    return FetchUserUseCase(repository)
```

---

## Exécution concurrente

Utilisez `asyncio.gather()` pour exécuter plusieurs AsyncUseCases en parallèle.

```python
import asyncio


@app.get("/dashboard")
async def dashboard(
    user_id: int,
    fetch_user: FetchUserUseCase = Depends(get_fetch_user_use_case),
    fetch_stats: FetchStatsUseCase = Depends(get_fetch_stats_use_case),
) -> JSONResponse:
    user, stats = await asyncio.gather(
        fetch_user.execute(FetchUserInput(user_id=user_id)),
        fetch_stats.execute(FetchStatsInput(user_id=user_id)),
    )
    return JSONResponse({"user": user.name, "stats": stats.count})
```

---

## Note sur isinstance()

`AsyncUseCaseProtocol` est `@runtime_checkable`, mais `isinstance()` vérifie seulement la
présence d'un attribut `execute` (il ne distingue pas sync d'async).

```python
# isinstance() renvoie True même pour un UseCase sync (faux positif)
isinstance(sync_use_case, AsyncUseCaseProtocol)  # → True

# la bonne façon de vérifier l'async
import inspect
inspect.iscoroutinefunction(use_case.execute)  # → True/False
```

La sécurité de type est garantie par l'analyse statique de `mypy --strict`. Voir ADR-0010 pour les détails.

---

## Le problème des appels DB synchrones bloquants

Effectuer un appel DB synchrone (p. ex. l'API sync de SQLAlchemy) dans un handler `async def`
bloque la boucle d'événements et paralyse les autres requêtes.

```python
# ❌ un appel DB synchrone dans async def bloque
@app.get("/notes")
async def list_notes() -> JSONResponse:
    notes = session.execute(select(Note)).scalars().all()  # bloque !
    return JSONResponse(...)
```

**Solution 1 : l'exécuter dans un pool de threads avec `run_in_threadpool`**

```python
from nene2.middleware import run_in_threadpool

@app.get("/notes")
async def list_notes() -> JSONResponse:
    notes = await run_in_threadpool(session.execute, select(Note))
    return JSONResponse(...)
```

**Solution 2 : utiliser un handler `def` (synchrone)**

Si vous utilisez une DB synchrone, ne rendez pas le handler `async def`. FastAPI l'exécute
automatiquement dans un pool de threads.

```python
# ✅ handler def + DB synchrone = aucun problème
@app.get("/notes")
def list_notes() -> JSONResponse:
    notes = session.execute(select(Note)).scalars().all()
    return JSONResponse(...)
```

**Solution 3 : migrer vers l'API async de SQLAlchemy**

À long terme, envisagez de migrer vers l'API async de SQLAlchemy (`AsyncSession`).
