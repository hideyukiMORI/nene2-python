# How-to: FastAPI Depends パターン

FastAPI の `Depends()` の使い方と、`Annotated` スタイルへの統一パターンを説明する。

---

## 1. 2 つの Depends スタイル

FastAPI には `Depends()` の書き方が 2 通りある。

```python
# スタイル A: = Depends(...) （デフォルト値スタイル）
def handler(
    use_case: FetchUserUseCase = Depends(get_fetch_user_use_case),
) -> JSONResponse: ...

# スタイル B: Annotated[T, Depends(...)] （Annotated スタイル）
def handler(
    use_case: Annotated[FetchUserUseCase, Depends(get_fetch_user_use_case)],
) -> JSONResponse: ...
```

**推奨: `Annotated` スタイル（スタイル B）に統一する**

---

## 2. スタイル混在で起きる SyntaxError

`= Depends(...)` と `Annotated[T, Depends()]` を同じ関数に混在させると **SyntaxError** が発生する。

```python
# ❌ SyntaxError: parameter without a default follows parameter with a default
def list_articles(
    filter_: ArticleFilter = Depends(get_filter),   # デフォルト値あり
    pagination: Annotated[PaginationQueryParser, Depends()],  # デフォルト値なし
) -> JSONResponse: ...

# ✅ Annotated スタイルに統一
def list_articles(
    filter_: Annotated[ArticleFilter, Depends(get_filter)],
    pagination: Annotated[PaginationQueryParser, Depends()],
) -> JSONResponse: ...
```

Python の仕様として、デフォルト値を持つ引数の後にデフォルト値なしの引数は置けない。
`Annotated[T, Depends()]` はデフォルト値を持たないため、`= Depends(...)` の後には書けない。

---

## 3. PaginationQueryParser の正しい使い方

`PaginationQueryParser` は `Annotated[T, Depends()]` で使う。`as_depends()` は存在しない。

```python
from typing import Annotated
from fastapi import Depends
from nene2.http import PaginationQueryParser

# ✅ 正しい
def list_items(
    pagination: Annotated[PaginationQueryParser, Depends()],
) -> JSONResponse:
    result = use_case.execute(pagination.limit, pagination.offset)
    ...

# ❌ as_depends() は存在しない
def list_items(
    pagination: PaginationQueryParser = Depends(PaginationQueryParser.as_depends()),
) -> JSONResponse: ...
```

---

## 4. カスタムフィルター + ページネーション

複数の `Depends()` パラメーターを組み合わせる場合はすべて `Annotated` スタイルで統一する。

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
    # フィルター: filter_.status, filter_.tag
    # ページネーション: pagination.limit, pagination.offset
    ...
```

---

## 5. Depends でキャッシュを注入する

`Annotated` スタイルで `app.state` のキャッシュを注入する例。

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
