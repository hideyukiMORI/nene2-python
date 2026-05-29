# How-to: lifespan and app.state

Resource management patterns using FastAPI's `lifespan` context manager and
`app.state`.

---

## 1. Basic lifespan pattern

Resources that are initialized at app startup and cleaned up at shutdown — DB
connections, caches, external clients — are managed with `lifespan`.

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # startup: initialize resources
    app.state.db = await create_db_connection()
    yield
    # shutdown: clean up
    await app.state.db.close()

app = FastAPI(lifespan=lifespan)
```

---

## 2. Type-safe access to app.state

`app.state` is a `starlette.datastructures.State` object to which arbitrary
attributes can be added dynamically. Since it has no type annotations, type
checking doesn't apply when accessing it.

**Recommended: define typed accessor functions**

```python
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

def get_db(request: Request) -> AsyncSession:
    db: AsyncSession = request.app.state.db  # type: ignore[attr-defined]  # reason: always set by lifespan
    return db
```

Or define a typed wrapper:

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

## 3. TestClient and lifespan

If you use `TestClient` the usual way (without the context manager), lifespan does
not run.

```python
# ❌ lifespan does not run
client = TestClient(app)
r = client.get("/")  # AttributeError because app.state.db is unset

# ✅ run lifespan with a with-block
with TestClient(app) as client:
    r = client.get("/")  # lifespan starts up and shuts down
```

Note that if another test ran `with TestClient(app)` first, `app.state` may
persist and it might happen to work even without `with`. That is a test-order
dependent bug, so always use a `with`-block.

**pytest fixture pattern**:

```python
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
```

Make the return type `Generator[TestClient, None, None]` (just `TestClient` is a
type error).

---

## 4. Managing a TtlCache via app.state

Storing `nene2.cache.TtlCache` on `app.state` avoids a global variable in tests.

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
    # TtlCache needs no cleanup (memory only)

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

**Global variable vs. app.state**:

| Approach | Pro | Con |
|---|---|---|
| Global variable | Simple | State shared across tests |
| `app.state` | Resettable per test with an independent `TestClient` | Requires `type: ignore` |

---

## 5. Values set on app.state disappear after lifespan

Set values on `app.state` inside `lifespan`. The `startup` event (old API) is
deprecated in FastAPI 0.93+.

```python
# ❌ old API (deprecated)
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
