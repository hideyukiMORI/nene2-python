# 操作指南：lifespan 与 app.state

使用 FastAPI 的 `lifespan` 上下文管理器和 `app.state` 管理资源的模式。

---

## 1. 基本 lifespan 模式

在应用启动时初始化、在关闭时清理的资源（数据库连接、缓存、外部客户端），使用 `lifespan` 管理。

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 启动：初始化资源
    app.state.db = await create_db_connection()
    yield
    # 关闭：清理资源
    await app.state.db.close()

app = FastAPI(lifespan=lifespan)
```

---

## 2. 对 app.state 进行类型安全访问

`app.state` 是一个 `starlette.datastructures.State` 对象，可以动态添加任意属性。由于没有类型注解，访问时类型检查不适用。

**推荐：定义带类型的访问器函数**

```python
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

def get_db(request: Request) -> AsyncSession:
    db: AsyncSession = request.app.state.db  # type: ignore[attr-defined]  # reason: always set by lifespan
    return db
```

或定义带类型的包装器：

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

## 3. TestClient 与 lifespan

如果以普通方式使用 `TestClient`（不使用上下文管理器），lifespan 不会运行。

```python
# ❌ lifespan 不会运行
client = TestClient(app)
r = client.get("/")  # AttributeError，因为 app.state.db 未设置

# ✅ 使用 with 块运行 lifespan
with TestClient(app) as client:
    r = client.get("/")  # lifespan 正常启动和关闭
```

注意，如果另一个测试已经运行了 `with TestClient(app)`，`app.state` 可能持续存在，看起来没有 `with` 也能工作。这是依赖测试顺序的 bug，请始终使用 `with` 块。

**pytest fixture 模式**：

```python
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
```

返回类型应为 `Generator[TestClient, None, None]`（单独的 `TestClient` 会导致类型错误）。

---

## 4. 通过 app.state 管理 TtlCache

将 `nene2.cache.TtlCache` 存储在 `app.state` 上，避免测试中的全局变量。

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
    # TtlCache 无需清理（仅内存）

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

**全局变量 vs. app.state**：

| 方式 | 优点 | 缺点 |
|---|---|---|
| 全局变量 | 简单 | 测试间共享状态 |
| `app.state` | 每个测试可通过独立 `TestClient` 重置 | 需要 `type: ignore` |

---

## 5. app.state 上设置的值在 lifespan 之外消失

在 `lifespan` 内设置 `app.state` 的值。旧的 `startup` 事件 API 在 FastAPI 0.93+ 中已废弃。

```python
# ❌ 旧 API（已废弃）
@app.on_event("startup")
async def startup() -> None:
    app.state.db = await create_db_connection()

# ✅ 使用 lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.db = await create_db_connection()
    yield
    await app.state.db.close()
```
