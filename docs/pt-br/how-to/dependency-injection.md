# Como fazer: padrões de FastAPI Depends

Como usar o `Depends()` do FastAPI e a convenção de padronizar no estilo `Annotated`.

---

## 1. Dois estilos de Depends

O FastAPI tem duas formas de escrever `Depends()`.

```python
# Estilo A: = Depends(...) (estilo de valor padrão)
def handler(
    use_case: FetchUserUseCase = Depends(get_fetch_user_use_case),
) -> JSONResponse: ...

# Estilo B: Annotated[T, Depends(...)] (estilo Annotated)
def handler(
    use_case: Annotated[FetchUserUseCase, Depends(get_fetch_user_use_case)],
) -> JSONResponse: ...
```

**Recomendado: padronize no estilo `Annotated` (Estilo B).**

---

## 2. SyntaxError ao misturar estilos

Misturar `= Depends(...)` e `Annotated[T, Depends()]` na mesma função levanta um
**SyntaxError**.

```python
# ❌ SyntaxError: parameter without a default follows parameter with a default
def list_articles(
    filter_: ArticleFilter = Depends(get_filter),   # tem um padrão
    pagination: Annotated[PaginationQueryParser, Depends()],  # sem padrão
) -> JSONResponse: ...

# ✅ padronize no estilo Annotated
def list_articles(
    filter_: Annotated[ArticleFilter, Depends(get_filter)],
    pagination: Annotated[PaginationQueryParser, Depends()],
) -> JSONResponse: ...
```

Como regra do Python, um parâmetro sem valor padrão não pode vir depois de um com valor padrão.
`Annotated[T, Depends()]` não tem padrão, então não pode vir depois de `= Depends(...)`.

---

## 3. A forma correta de usar PaginationQueryParser

Use `PaginationQueryParser` com `Annotated[T, Depends()]`. Não existe `as_depends()`.

```python
from typing import Annotated
from fastapi import Depends
from nene2.http import PaginationQueryParser

# ✅ correto
def list_items(
    pagination: Annotated[PaginationQueryParser, Depends()],
) -> JSONResponse:
    result = use_case.execute(pagination.limit, pagination.offset)
    ...

# ❌ as_depends() não existe
def list_items(
    pagination: PaginationQueryParser = Depends(PaginationQueryParser.as_depends()),
) -> JSONResponse: ...
```

---

## 4. Filtro customizado + paginação

Ao combinar múltiplos parâmetros `Depends()`, padronize todos no estilo `Annotated`.

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
    # filtro: filter_.status, filter_.tag
    # paginação: pagination.limit, pagination.offset
    ...
```

---

## 5. Injetando um cache via Depends

Um exemplo de injeção de um cache de `app.state` no estilo `Annotated`.

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
