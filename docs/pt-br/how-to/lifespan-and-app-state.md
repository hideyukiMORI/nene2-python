# Como fazer: lifespan e app.state

Padrões de gerenciamento de recursos usando o context manager `lifespan` do FastAPI e
`app.state`.

---

## 1. Padrão básico de lifespan

Recursos inicializados na inicialização do app e limpos no shutdown — conexões de DB,
caches, clientes externos — são gerenciados com `lifespan`.

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # startup: inicializar recursos
    app.state.db = await create_db_connection()
    yield
    # shutdown: limpar
    await app.state.db.close()

app = FastAPI(lifespan=lifespan)
```

---

## 2. Acesso type-safe ao app.state

`app.state` é um objeto `starlette.datastructures.State` ao qual atributos arbitrários
podem ser adicionados dinamicamente. Como não tem anotações de tipo, a verificação de tipos
não se aplica ao acessá-lo.

**Recomendado: definir funções acessoras tipadas**

```python
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

def get_db(request: Request) -> AsyncSession:
    db: AsyncSession = request.app.state.db  # type: ignore[attr-defined]  # reason: always set by lifespan
    return db
```

Ou defina um wrapper tipado:

```python
from dataclasses import dataclass

@dataclass
class AppState:
    db: AsyncSession
    cache: RedisClient

def get_app_state(request: Request) -> AppState:
    return AppState(
        db=request.app.state.db,
        cache=request.app.state.cache,
    )
```

---

## 3. TestClient e lifespan

Se você usar `TestClient` da forma usual (sem o context manager), o lifespan não executa.

```python
# ❌ o lifespan não executa
client = TestClient(app)
r = client.get("/")  # AttributeError porque app.state.db não está definido

# ✅ execute o lifespan com um bloco with
with TestClient(app) as client:
    r = client.get("/")  # o lifespan inicia e encerra
```

Note que se outro teste executou `with TestClient(app)` antes, `app.state` pode
persistir e pode acontecer de funcionar mesmo sem `with`. Isso é um bug dependente
de ordem de testes, então sempre use um bloco `with`.

**Padrão de fixture pytest**:

```python
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
```

Faça o tipo de retorno `Generator[TestClient, None, None]` (apenas `TestClient` é um
erro de tipo).

---

## 4. Gerenciando um TtlCache via app.state

Armazenar `nene2.cache.TtlCache` em `app.state` evita uma variável global nos testes.

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from nene2.cache import TtlCache

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.cache = TtlCache[dict[str, object]](ttl_seconds=60.0)
    yield
    # TtlCache não precisa de limpeza (apenas memória)

app = FastAPI(lifespan=lifespan)


def get_cache(request: Request) -> TtlCache[dict[str, object]]:
    cache: TtlCache[dict[str, object]] = request.app.state.cache  # type: ignore[attr-defined]  # reason: always set by lifespan
    return cache


@app.get("/items/{item_id}")
def get_item(
    item_id: int,
    cache: TtlCache[dict[str, object]] = Depends(get_cache),
) -> JSONResponse:
    key = f"item:{item_id}"
    if (cached := cache.get(key)) is not None:
        return JSONResponse({"source": "cache", **cached})
    result = {"item_id": item_id, "name": f"Item {item_id}"}
    cache.set(key, result)
    return JSONResponse({"source": "fresh", **result})
```

**Variável global vs. app.state**:

| Abordagem | Prós | Contras |
|---|---|---|
| Variável global | Simples | Estado compartilhado entre testes |
| `app.state` | Resetável por teste com um `TestClient` independente | Requer `type: ignore` |

---

## 5. Valores definidos em app.state desaparecem após o lifespan

Defina valores em `app.state` dentro do `lifespan`. O evento `startup` (API antiga) está
depreciado no FastAPI 0.93+.

```python
# ❌ API antiga (depreciada)
@app.on_event("startup")
async def startup() -> None:
    app.state.db = await create_db_connection()

# ✅ use lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.db = await create_db_connection()
    yield
    await app.state.db.close()
```
