# Guide pratique : les schémas FastAPI Depends

Comment utiliser `Depends()` de FastAPI, et la convention de se standardiser sur le style `Annotated`.

---

## 1. Deux styles Depends

FastAPI propose deux façons d'écrire `Depends()`.

```python
# Style A : = Depends(...) (style valeur par défaut)
def handler(
    use_case: FetchUserUseCase = Depends(get_fetch_user_use_case),
) -> JSONResponse: ...

# Style B : Annotated[T, Depends(...)] (style Annotated)
def handler(
    use_case: Annotated[FetchUserUseCase, Depends(get_fetch_user_use_case)],
) -> JSONResponse: ...
```

**Recommandé : se standardiser sur le style `Annotated` (Style B).**

---

## 2. SyntaxError en mélangeant les styles

Mélanger `= Depends(...)` et `Annotated[T, Depends()]` dans la même fonction lève une
**SyntaxError**.

```python
# ❌ SyntaxError: parameter without a default follows parameter with a default
def list_articles(
    filter_: ArticleFilter = Depends(get_filter),   # a une valeur par défaut
    pagination: Annotated[PaginationQueryParser, Depends()],  # sans valeur par défaut
) -> JSONResponse: ...

# ✅ se standardiser sur le style Annotated
def list_articles(
    filter_: Annotated[ArticleFilter, Depends(get_filter)],
    pagination: Annotated[PaginationQueryParser, Depends()],
) -> JSONResponse: ...
```

Selon les règles Python, un paramètre sans valeur par défaut ne peut pas suivre un paramètre
avec une valeur par défaut. `Annotated[T, Depends()]` n'a pas de valeur par défaut, donc il ne
peut pas venir après `= Depends(...)`.

---

## 3. La bonne façon d'utiliser PaginationQueryParser

Utilisez `PaginationQueryParser` avec `Annotated[T, Depends()]`. Il n'y a pas de `as_depends()`.

```python
from typing import Annotated
from fastapi import Depends
from nene2.http import PaginationQueryParser

# ✅ correct
def list_items(
    pagination: Annotated[PaginationQueryParser, Depends()],
) -> JSONResponse:
    result = use_case.execute(pagination.limit, pagination.offset)
    ...

# ❌ as_depends() n'existe pas
def list_items(
    pagination: PaginationQueryParser = Depends(PaginationQueryParser.as_depends()),
) -> JSONResponse: ...
```

---

## 4. Filtre personnalisé + pagination

Quand vous combinez plusieurs paramètres `Depends()`, standardisez-les tous sur le style `Annotated`.

```python
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, FastAPI, Query
from fastapi.responses import JSONResponse

from nene2.http import PaginationQueryParser


class Status(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True, slots=True)
class ItemFilter:
    status: Status | None
    tag: str | None


def get_item_filter(
    status: Annotated[Status | None, Query()] = None,
    tag: Annotated[str | None, Query(max_length=50)] = None,
) -> ItemFilter:
    return ItemFilter(status=status, tag=tag)


@app.get("/items")
def list_items(
    filter_: Annotated[ItemFilter, Depends(get_item_filter)],
    pagination: Annotated[PaginationQueryParser, Depends()],
) -> JSONResponse:
    # filter : filter_.status, filter_.tag
    # pagination : pagination.limit, pagination.offset
    ...
```

---

## 5. Injecter un cache via Depends

Exemple d'injection d'un cache `app.state` dans le style `Annotated`.

```python
from fastapi import Request
from nene2.cache import TtlCache

def get_cache(request: Request) -> TtlCache[dict[str, object]]:
    return request.app.state.cache  # type: ignore[attr-defined]

@app.get("/items/{item_id}")
def get_item(
    item_id: int,
    cache: Annotated[TtlCache[dict[str, object]], Depends(get_cache)],
) -> JSONResponse:
    ...
```
