# Como fazer: integrar AsyncUseCase com FastAPI

## Implementação básica de AsyncUseCaseProtocol

`AsyncUseCaseProtocol` é um Protocol (tipagem estrutural), então não é necessária herança.
Basta implementar `async def execute(self, input_: I) -> O` para conformar.

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
        # trabalho assíncrono como chamada a API externa ou acesso ao DB
        return FetchUserOutput(user_id=input_.user_id, name="Alice")
```

---

## Integração com FastAPI Depends

Passar uma função factory para `Depends()` é o padrão padrão.

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

## DI para um UseCase com dependências externas

Um UseCase que recebe um repository ou cliente externo tem esses injetados via
Depends também.

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

## Execução concorrente

Use `asyncio.gather()` para executar múltiplos AsyncUseCases de forma concorrente.

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

## Uma observação sobre isinstance()

`AsyncUseCaseProtocol` é `@runtime_checkable`, mas `isinstance()` verifica apenas a
presença do atributo `execute` (não distingue sync de async).

```python
# isinstance() retorna True para um UseCase síncrono também (falso positivo)
isinstance(sync_use_case, AsyncUseCaseProtocol)  # → True

# a forma correta de verificar async
import inspect
inspect.iscoroutinefunction(use_case.execute)  # → True/False
```

A segurança de tipos é garantida pela análise estática do `mypy --strict`. Veja ADR-0010 para detalhes.

---

## O problema de bloqueio em chamadas DB síncronas

Fazer uma chamada DB síncrona (ex: a API síncrona do SQLAlchemy) dentro de um handler `async def`
bloqueia o event loop e paralisa outras requisições.

```python
# ❌ uma chamada DB síncrona dentro de async def bloqueia
@app.get("/notes")
async def list_notes() -> JSONResponse:
    notes = session.execute(select(Note)).scalars().all()  # bloqueia!
    return JSONResponse(...)
```

**Solução 1: execute em um thread pool com `run_in_threadpool`**

```python
from nene2.middleware import run_in_threadpool

@app.get("/notes")
async def list_notes() -> JSONResponse:
    notes = await run_in_threadpool(session.execute, select(Note))
    return JSONResponse(...)
```

**Solução 2: use um handler `def` (síncrono)**

Se você usa DB síncrono, não use `async def` no handler. O FastAPI o executa em um
thread pool automaticamente.

```python
# ✅ handler def + DB síncrono = sem problema
@app.get("/notes")
def list_notes() -> JSONResponse:
    notes = session.execute(select(Note)).scalars().all()
    return JSONResponse(...)
```

**Solução 3: migrar para a API async do SQLAlchemy**

A longo prazo, considere migrar para a API async do SQLAlchemy (`AsyncSession`).
