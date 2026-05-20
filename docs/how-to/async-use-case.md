# How-to: AsyncUseCase と FastAPI の統合

## AsyncUseCaseProtocol の基本実装

`AsyncUseCaseProtocol` は Protocol（構造的部分型）なので継承不要です。
`async def execute(self, input_: I) -> O` を実装するだけで適合します。

```python
from dataclasses import dataclass
from nene2.use_case import AsyncUseCaseProtocol


@dataclass(frozen=True, slots=True)
class FetchUserInput:
    user_id: int


@dataclass(frozen=True, slots=True)
class FetchUserOutput:
    user_id: int
    name: str


class FetchUserUseCase:
    async def execute(self, input_: FetchUserInput) -> FetchUserOutput:
        # 外部 API 呼び出し・DB アクセスなど非同期処理
        return FetchUserOutput(user_id=input_.user_id, name="Alice")
```

---

## FastAPI Depends との統合

ファクトリ関数を `Depends()` に渡すのが標準パターンです。

```python
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


def get_fetch_user_use_case() -> FetchUserUseCase:
    return FetchUserUseCase()


@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    use_case: FetchUserUseCase = Depends(get_fetch_user_use_case),
) -> JSONResponse:
    result = await use_case.execute(FetchUserInput(user_id=user_id))
    return JSONResponse({"user_id": result.user_id, "name": result.name})
```

---

## 外部依存を持つ UseCase の DI

リポジトリや外部クライアントを受け取る UseCase は、依存も Depends で注入します。

```python
class FetchUserUseCase:
    def __init__(self, repository: UserRepositoryInterface) -> None:
        self._repository = repository

    async def execute(self, input_: FetchUserInput) -> FetchUserOutput:
        user = await self._repository.find_by_id(input_.user_id)
        return FetchUserOutput(user_id=user.id, name=user.name)


def get_user_repository() -> UserRepositoryInterface:
    return InMemoryUserRepository()


def get_fetch_user_use_case(
    repository: UserRepositoryInterface = Depends(get_user_repository),
) -> FetchUserUseCase:
    return FetchUserUseCase(repository)
```

---

## 並行実行

複数の AsyncUseCase を並行実行するには `asyncio.gather()` を使います。

```python
import asyncio


@app.get("/dashboard")
async def dashboard(
    user_id: int,
    fetch_user: FetchUserUseCase = Depends(get_fetch_user_use_case),
    fetch_stats: FetchStatsUseCase = Depends(get_fetch_stats_use_case),
) -> JSONResponse:
    user, stats = await asyncio.gather(
        fetch_user.execute(FetchUserInput(user_id=user_id)),
        fetch_stats.execute(FetchStatsInput(user_id=user_id)),
    )
    return JSONResponse({"user": user.name, "stats": stats.count})
```

---

## isinstance() の注意点

`AsyncUseCaseProtocol` は `@runtime_checkable` ですが、`isinstance()` は
`execute` 属性の存在のみを確認します（sync/async の区別はしません）。

```python
# isinstance() は sync UseCase も True を返す（false positive）
isinstance(sync_use_case, AsyncUseCaseProtocol)  # → True

# 正しい非同期確認方法
import inspect
inspect.iscoroutinefunction(use_case.execute)  # → True/False
```

型安全性は `mypy --strict` の静的解析で保証します。詳細は ADR-0010 を参照してください。

---

## 同期 DB 呼び出しのブロッキング問題

`async def` ハンドラーで同期の DB 呼び出し（SQLAlchemy sync API 等）を行うと、イベントループをブロックして他のリクエストが詰まる。

```python
# ❌ async def 内での同期 DB 呼び出しはブロッキング
@app.get("/notes")
async def list_notes() -> JSONResponse:
    notes = session.execute(select(Note)).scalars().all()  # ブロック！
    return JSONResponse(...)
```

**解決策1: `run_in_threadpool` でスレッドプールで実行する**

```python
from nene2.middleware import run_in_threadpool

@app.get("/notes")
async def list_notes() -> JSONResponse:
    notes = await run_in_threadpool(session.execute, select(Note))
    return JSONResponse(...)
```

**解決策2: `def`（同期）ハンドラーを使う**

同期 DB を使う場合は、ハンドラーを `async def` にしない。FastAPI が自動でスレッドプールで実行する。

```python
# ✅ def ハンドラー + 同期 DB = 問題なし
@app.get("/notes")
def list_notes() -> JSONResponse:
    notes = session.execute(select(Note)).scalars().all()
    return JSONResponse(...)
```

**解決策3: SQLAlchemy async API に移行する**

長期的には SQLAlchemy の async API（`AsyncSession`）への移行を検討する。
