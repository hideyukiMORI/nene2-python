# How-to: Lifespan und app.state

Ressourcenverwaltungsmuster mit FastAPIs `lifespan`-Kontextmanager und `app.state`.

---

## 1. Grundlegendes Lifespan-Muster

Ressourcen, die beim App-Start initialisiert und beim Herunterfahren bereinigt werden — DB-Verbindungen, Caches, externe Clients — werden mit `lifespan` verwaltet.

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup: Ressourcen initialisieren
    app.state.db = await create_db_connection()
    yield
    # Shutdown: bereinigen
    await app.state.db.close()

app = FastAPI(lifespan=lifespan)
```

---

## 2. Typsicherer Zugriff auf app.state

`app.state` ist ein `starlette.datastructures.State`-Objekt, dem beliebige Attribute dynamisch hinzugefügt werden können. Da es keine Typannotationen hat, gilt die Typprüfung beim Zugriff nicht.

**Empfohlen: typisierte Zugriffsfunktionen definieren**

```python
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

def get_db(request: Request) -> AsyncSession:
    db: AsyncSession = request.app.state.db  # type: ignore[attr-defined]  # reason: always set by lifespan
    return db
```

Oder einen typisierten Wrapper definieren:

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

## 3. TestClient und Lifespan

Wenn Sie `TestClient` auf gewöhnliche Weise verwenden (ohne den Kontextmanager), läuft Lifespan nicht.

```python
# ❌ Lifespan läuft nicht
client = TestClient(app)
r = client.get("/")  # AttributeError, da app.state.db nicht gesetzt ist

# ✅ Lifespan mit einem with-Block ausführen
with TestClient(app) as client:
    r = client.get("/")  # Lifespan startet und fährt herunter
```

Beachten Sie, dass wenn ein anderer Test zuerst `with TestClient(app)` ausgeführt hat, `app.state` möglicherweise bestehen bleibt und es auch ohne `with` zufällig funktioniert. Das ist ein testordnungsabhängiger Fehler, daher verwenden Sie immer einen `with`-Block.

**pytest-Fixture-Muster**:

```python
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
```

Machen Sie den Rückgabetyp zu `Generator[TestClient, None, None]` (nur `TestClient` ist ein Typfehler).

---

## 4. Einen TtlCache über app.state verwalten

Das Speichern von `nene2.cache.TtlCache` auf `app.state` vermeidet eine globale Variable in Tests.

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
    # TtlCache benötigt keine Bereinigung (nur Speicher)

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

**Globale Variable vs. app.state**:

| Ansatz | Vorteil | Nachteil |
|---|---|---|
| Globale Variable | Einfach | Zustand wird über Tests hinweg geteilt |
| `app.state` | Pro Test mit einem unabhängigen `TestClient` zurücksetzbar | Erfordert `type: ignore` |

---

## 5. Auf app.state gesetzte Werte verschwinden nach Lifespan

Setzen Sie Werte auf `app.state` innerhalb von `lifespan`. Das `startup`-Ereignis (alte API) ist in FastAPI 0.93+ veraltet.

```python
# ❌ alte API (veraltet)
@app.on_event("startup")
async def startup() -> None:
    app.state.db = await create_db_connection()

# ✅ Lifespan verwenden
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.db = await create_db_connection()
    yield
    await app.state.db.close()
```
