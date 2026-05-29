# 操作指南：在 FastAPI 中集成 AsyncUseCase

## AsyncUseCaseProtocol 基本实现

`AsyncUseCaseProtocol` 是一个 Protocol（结构化子类型），无需继承，只要实现 `async def execute(self, input_: I) -> O` 即可满足协议。

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
        # 异步操作，例如外部 API 调用或数据库访问
        return FetchUserOutput(user_id=input_.user_id, name="Alice")
```

---

## 与 FastAPI Depends 集成

向 `Depends()` 传入工厂函数是标准模式。

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

## 含外部依赖的 UseCase 的依赖注入

需要 repository 或外部客户端的 UseCase，也通过 Depends 进行注入。

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

## 并发执行

使用 `asyncio.gather()` 并发运行多个 AsyncUseCase。

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

## 关于 isinstance() 的注意事项

`AsyncUseCaseProtocol` 是 `@runtime_checkable` 的，但 `isinstance()` 只检查是否存在 `execute` 属性（不区分同步和异步）。

```python
# isinstance() 对同步 UseCase 也会返回 True（误报）
isinstance(sync_use_case, AsyncUseCaseProtocol)  # → True

# 正确的异步检查方式
import inspect
inspect.iscoroutinefunction(use_case.execute)  # → True/False
```

类型安全由 `mypy --strict` 静态分析保证。详见 ADR-0010。

---

## 同步数据库调用的阻塞问题

在 `async def` handler 中调用同步数据库接口（例如 SQLAlchemy 同步 API）会阻塞事件循环，导致其他请求停滞。

```python
# ❌ 在 async def 中调用同步数据库会阻塞
@app.get("/notes")
async def list_notes() -> JSONResponse:
    notes = session.execute(select(Note)).scalars().all()  # 阻塞！
    return JSONResponse(...)
```

**方案一：使用 `run_in_threadpool` 在线程池中运行**

```python
from nene2.middleware import run_in_threadpool

@app.get("/notes")
async def list_notes() -> JSONResponse:
    notes = await run_in_threadpool(session.execute, select(Note))
    return JSONResponse(...)
```

**方案二：使用 `def`（同步）handler**

如果使用同步数据库，不要将 handler 定义为 `async def`。FastAPI 会自动在线程池中运行它。

```python
# ✅ def handler + 同步数据库 = 无问题
@app.get("/notes")
def list_notes() -> JSONResponse:
    notes = session.execute(select(Note)).scalars().all()
    return JSONResponse(...)
```

**方案三：迁移到 SQLAlchemy 异步 API**

从长远看，考虑迁移到 SQLAlchemy 的异步 API（`AsyncSession`）。
