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

## 4. app.state に設定した値が lifespan 後に消える

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
