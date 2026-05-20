# How-to: Lifespan と app.state

FastAPI の `lifespan` コンテキストマネージャーと `app.state` を使ったリソース管理パターンを説明する。

---

## 1. Lifespan の基本パターン

DB 接続・キャッシュ・外部クライアントなど、アプリ起動時に初期化して終了時にクリーンアップするリソースは `lifespan` で管理する。

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 起動時: リソース初期化
    app.state.db = await create_db_connection()
    yield
    # 終了時: クリーンアップ
    await app.state.db.close()

app = FastAPI(lifespan=lifespan)
```

---

## 2. app.state の型安全なアクセス

`app.state` は `starlette.datastructures.State` オブジェクトで、任意の属性を動的に追加できる。型アノテーションがないため、アクセス時に型チェックが効かない。

**推奨: 型付きアクセサー関数を定義する**

```python
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

def get_db(request: Request) -> AsyncSession:
    db: AsyncSession = request.app.state.db  # type: ignore[attr-defined]  # reason: lifespan で確実に設定される
    return db
```

または、型付きラッパーを定義する:

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

## 3. TestClient と lifespan

`TestClient` を通常の使い方（コンテキストマネージャーなし）だと、lifespan が実行されない。

```python
# ❌ lifespan が実行されない
client = TestClient(app)
r = client.get("/")  # app.state.db が未設定で AttributeError

# ✅ with ブロックで lifespan を実行する
with TestClient(app) as client:
    r = client.get("/")  # lifespan が起動・終了する
```

ただし、別のテストが先に `with TestClient(app)` を実行していると `app.state` が持続し、`with` なしでも偶然動作することがある。これはテスト順依存のバグになりうるため、常に `with` ブロックを使う。

**pytest fixture パターン**:

```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
```

---

## 4. TtlCache を app.state で管理する

`nene2.cache.TtlCache` を `app.state` に格納すると、テスト時にグローバル変数を避けられる。

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
    # TtlCache はクリーンアップ不要（メモリのみ）

app = FastAPI(lifespan=lifespan)


def get_cache(request: Request) -> TtlCache[dict[str, object]]:
    cache: TtlCache[dict[str, object]] = request.app.state.cache  # type: ignore[attr-defined]  # reason: lifespan で確実に設定される
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

**グローバル変数 vs app.state の比較**:

| 方法 | メリット | デメリット |
|---|---|---|
| グローバル変数 | シンプル | テスト間で状態が共有される |
| `app.state` | テストごとに独立した `TestClient` でリセット可能 | `type: ignore` が必要 |

---

## 6. app.state に設定した値が lifespan 後に消える

`app.state` への設定は `lifespan` 内で行う。`startup` イベント（旧 API）は FastAPI 0.93+ では非推奨。

```python
# ❌ 旧 API（非推奨）
@app.on_event("startup")
async def startup() -> None:
    app.state.db = await create_db_connection()

# ✅ lifespan を使う
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.db = await create_db_connection()
    yield
    await app.state.db.close()
```
