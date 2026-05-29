# How-to: FastAPI Depends-Muster

So verwenden Sie FastAPIs `Depends()` und die Konvention, sich auf den `Annotated`-Stil zu standardisieren.

---

## 1. Zwei Depends-Stile

FastAPI bietet zwei Möglichkeiten, `Depends()` zu schreiben.

```python
# Stil A: = Depends(...) (Standardwert-Stil)
def handler(
    use_case: FetchUserUseCase = Depends(get_fetch_user_use_case),
) -> JSONResponse: ...

# Stil B: Annotated[T, Depends(...)] (Annotated-Stil)
def handler(
    use_case: Annotated[FetchUserUseCase, Depends(get_fetch_user_use_case)],
) -> JSONResponse: ...
```

**Empfohlen: Standardisieren Sie auf den `Annotated`-Stil (Stil B).**

---

## 2. SyntaxError beim Mischen der Stile

Das Mischen von `= Depends(...)` und `Annotated[T, Depends()]` in derselben Funktion löst einen **SyntaxError** aus.

```python
# ❌ SyntaxError: parameter without a default follows parameter with a default
def list_articles(
    filter_: ArticleFilter = Depends(get_filter),   # hat einen Standardwert
    pagination: Annotated[PaginationQueryParser, Depends()],  # kein Standardwert
) -> JSONResponse: ...

# ✅ auf den Annotated-Stil standardisieren
def list_articles(
    filter_: Annotated[ArticleFilter, Depends(get_filter)],
    pagination: Annotated[PaginationQueryParser, Depends()],
) -> JSONResponse: ...
```

Als Python-Regel kann ein Parameter ohne Standardwert nicht auf einen mit Standardwert folgen. `Annotated[T, Depends()]` hat keinen Standardwert, daher kann er nicht nach `= Depends(...)` kommen.

---

## 3. Die korrekte Verwendung von PaginationQueryParser

Verwenden Sie `PaginationQueryParser` mit `Annotated[T, Depends()]`. Es gibt kein `as_depends()`.

```python
from typing import Annotated
from fastapi import Depends
from nene2.http import PaginationQueryParser

# ✅ korrekt
def list_items(
    pagination: Annotated[PaginationQueryParser, Depends()],
) -> JSONResponse:
    result = use_case.execute(pagination.limit, pagination.offset)
    ...

# ❌ as_depends() existiert nicht
def list_items(
    pagination: PaginationQueryParser = Depends(PaginationQueryParser.as_depends()),
) -> JSONResponse: ...
```

---

## 4. Benutzerdefinierter Filter + Paginierung

Wenn mehrere `Depends()`-Parameter kombiniert werden, standardisieren Sie alle auf den `Annotated`-Stil.

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
    # Filter: filter_.status, filter_.tag
    # Paginierung: pagination.limit, pagination.offset
    ...
```

---

## 5. Einen Cache über Depends injizieren

Ein Beispiel für das Injizieren eines `app.state`-Caches im `Annotated`-Stil.

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
