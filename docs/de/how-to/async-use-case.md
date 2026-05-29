# How-to: AsyncUseCase mit FastAPI integrieren

## Grundlegende AsyncUseCaseProtocol-Implementierung

`AsyncUseCaseProtocol` ist ein Protocol (strukturelles Subtyping), daher ist keine Vererbung nötig. Die bloße Implementierung von `async def execute(self, input_: I) -> O` genügt.

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
        # asynchrone Arbeit wie ein externer API-Aufruf oder DB-Zugriff
        return FetchUserOutput(user_id=input_.user_id, name="Alice")
```

---

## Integration mit FastAPI Depends

Das Übergeben einer Factory-Funktion an `Depends()` ist das Standardmuster.

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

## DI für einen UseCase mit externen Abhängigkeiten

Ein UseCase, der ein Repository oder einen externen Client benötigt, erhält diese ebenfalls über Depends injiziert.

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

## Parallele Ausführung

Verwenden Sie `asyncio.gather()`, um mehrere AsyncUseCases gleichzeitig auszuführen.

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

## Hinweis zu isinstance()

`AsyncUseCaseProtocol` ist `@runtime_checkable`, aber `isinstance()` prüft nur das Vorhandensein eines `execute`-Attributs (unterscheidet nicht zwischen synchron und asynchron).

```python
# isinstance() gibt True auch für einen sync UseCase zurück (False Positive)
isinstance(sync_use_case, AsyncUseCaseProtocol)  # → True

# die korrekte Methode zur Prüfung auf async
import inspect
inspect.iscoroutinefunction(use_case.execute)  # → True/False
```

Typsicherheit wird durch statische Analyse mit `mypy --strict` gewährleistet. Einzelheiten finden Sie in ADR-0010.

---

## Das Blockierungsproblem bei synchronen DB-Aufrufen

Ein synchroner DB-Aufruf (z. B. über die synchrone SQLAlchemy-API) innerhalb eines `async def`-Handlers blockiert den Event-Loop und bremst andere Anfragen aus.

```python
# ❌ ein sync-DB-Aufruf innerhalb von async def blockiert
@app.get("/notes")
async def list_notes() -> JSONResponse:
    notes = session.execute(select(Note)).scalars().all()  # blockiert!
    return JSONResponse(...)
```

**Lösung 1: Im Thread-Pool mit `run_in_threadpool` ausführen**

```python
from nene2.middleware import run_in_threadpool

@app.get("/notes")
async def list_notes() -> JSONResponse:
    notes = await run_in_threadpool(session.execute, select(Note))
    return JSONResponse(...)
```

**Lösung 2: Einen `def`-(synchronen) Handler verwenden**

Wenn Sie eine synchrone DB verwenden, machen Sie den Handler nicht `async def`. FastAPI führt ihn automatisch in einem Thread-Pool aus.

```python
# ✅ def-Handler + synchrone DB = kein Problem
@app.get("/notes")
def list_notes() -> JSONResponse:
    notes = session.execute(select(Note)).scalars().all()
    return JSONResponse(...)
```

**Lösung 3: Zur asynchronen SQLAlchemy-API migrieren**

Erwägen Sie langfristig die Migration zur asynchronen API von SQLAlchemy (`AsyncSession`).
