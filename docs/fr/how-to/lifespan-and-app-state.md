# Guide pratique : lifespan et app.state

Schémas de gestion des ressources avec le gestionnaire de contexte `lifespan` de FastAPI et
`app.state`.

---

## 1. Schéma lifespan de base

Les ressources qui sont initialisées au démarrage de l'application et nettoyées à l'arrêt —
connexions DB, caches, clients externes — sont gérées avec `lifespan`.

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # démarrage : initialiser les ressources
    app.state.db = await create_db_connection()
    yield
    # arrêt : nettoyer
    await app.state.db.close()

app = FastAPI(lifespan=lifespan)
```

---

## 2. Accès typé à app.state

`app.state` est un objet `starlette.datastructures.State` auquel des attributs arbitraires
peuvent être ajoutés dynamiquement. Comme il n'a pas d'annotations de type, la vérification
de type ne s'applique pas lors de l'accès.

**Recommandé : définir des fonctions d'accès typées**

```python
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

def get_db(request: Request) -> AsyncSession:
    db: AsyncSession = request.app.state.db  # type: ignore[attr-defined]  # reason: always set by lifespan
    return db
```

Ou définir un wrapper typé :

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

## 3. TestClient et lifespan

Si vous utilisez `TestClient` de la façon habituelle (sans gestionnaire de contexte), lifespan
ne s'exécute pas.

```python
# ❌ lifespan ne s'exécute pas
client = TestClient(app)
r = client.get("/")  # AttributeError car app.state.db n'est pas défini

# ✅ exécuter lifespan avec un bloc with
with TestClient(app) as client:
    r = client.get("/")  # lifespan démarre et s'arrête
```

Notez que si un autre test a exécuté `with TestClient(app)` en premier, `app.state` peut
persister et il peut fonctionner même sans `with`. C'est un bug dépendant de l'ordre des tests,
donc utilisez toujours un bloc `with`.

**Schéma de fixture pytest** :

```python
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
```

Faites du type de retour `Generator[TestClient, None, None]` (juste `TestClient` est une erreur de type).

---

## 4. Gérer un TtlCache via app.state

Stocker `nene2.cache.TtlCache` dans `app.state` évite une variable globale dans les tests.

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
    # TtlCache n'a pas besoin de nettoyage (mémoire uniquement)

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

**Variable globale vs. app.state** :

| Approche | Pour | Contre |
|---|---|---|
| Variable globale | Simple | État partagé entre les tests |
| `app.state` | Réinitialisable par test avec un `TestClient` indépendant | Nécessite `type: ignore` |

---

## 5. Les valeurs définies dans app.state disparaissent après lifespan

Définissez les valeurs dans `app.state` à l'intérieur de `lifespan`. L'événement `startup`
(ancienne API) est déprécié dans FastAPI 0.93+.

```python
# ❌ ancienne API (dépréciée)
@app.on_event("startup")
async def startup() -> None:
    app.state.db = await create_db_connection()

# ✅ utiliser lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.db = await create_db_connection()
    yield
    await app.state.db.close()
```
