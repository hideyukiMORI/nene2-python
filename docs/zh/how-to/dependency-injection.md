# 操作指南：FastAPI Depends 模式

如何使用 FastAPI 的 `Depends()`，以及统一使用 `Annotated` 风格的约定。

---

## 1. 两种 Depends 写法

FastAPI 有两种写法。

```python
# 写法 A：= Depends(...)（默认值写法）
def handler(
    use_case: FetchUserUseCase = Depends(get_fetch_user_use_case),
) -> JSONResponse: ...

# 写法 B：Annotated[T, Depends(...)]（Annotated 写法）
def handler(
    use_case: Annotated[FetchUserUseCase, Depends(get_fetch_user_use_case)],
) -> JSONResponse: ...
```

**推荐：统一使用 `Annotated` 写法（写法 B）。**

---

## 2. 混用两种写法会导致 SyntaxError

在同一函数中混用 `= Depends(...)` 和 `Annotated[T, Depends()]` 会引发 **SyntaxError**。

```python
# ❌ SyntaxError：有默认值的参数后面不能跟没有默认值的参数
def list_articles(
    filter_: ArticleFilter = Depends(get_filter),   # 有默认值
    pagination: Annotated[PaginationQueryParser, Depends()],  # 无默认值
) -> JSONResponse: ...

# ✅ 统一使用 Annotated 写法
def list_articles(
    filter_: Annotated[ArticleFilter, Depends(get_filter)],
    pagination: Annotated[PaginationQueryParser, Depends()],
) -> JSONResponse: ...
```

这是 Python 的规则：没有默认值的参数不能跟在有默认值的参数后面。`Annotated[T, Depends()]` 没有默认值，因此不能放在 `= Depends(...)` 之后。

---

## 3. 正确使用 PaginationQueryParser 的方式

使用 `Annotated[T, Depends()]` 配合 `PaginationQueryParser`，不存在 `as_depends()`。

```python
from typing import Annotated
from fastapi import Depends
from nene2.http import PaginationQueryParser

# ✅ 正确
def list_items(
    pagination: Annotated[PaginationQueryParser, Depends()],
) -> JSONResponse:
    result = use_case.execute(pagination.limit, pagination.offset)
    ...

# ❌ as_depends() 不存在
def list_items(
    pagination: PaginationQueryParser = Depends(PaginationQueryParser.as_depends()),
) -> JSONResponse: ...
```

---

## 4. 自定义过滤器 + 分页

组合多个 `Depends()` 参数时，统一使用 `Annotated` 写法。

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
    # 过滤器：filter_.status, filter_.tag
    # 分页：pagination.limit, pagination.offset
    ...
```

---

## 5. 通过 Depends 注入缓存

使用 `Annotated` 写法注入 `app.state` 缓存的示例。

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
