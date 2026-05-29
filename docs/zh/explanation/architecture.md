# 架构概览

## 层次结构

nene2-python 遵循整洁架构（Clean Architecture），依赖关系由外向内单向流动。

```
┌─────────────────────────────────────────────┐
│  HTTP Handler (FastAPI router)              │
│  解析请求 → 调用 UseCase → 返回响应          │
├─────────────────────────────────────────────┤
│  UseCase                                    │
│  业务逻辑 — 不感知 HTTP 或数据库             │
├─────────────────────────────────────────────┤
│  RepositoryInterface (ABC)                  │
│  定义领域所需操作的契约                      │
├─────────────────────────────────────────────┤
│  ConcreteRepository                         │
│  SQLAlchemy / InMemory 具体实现             │
└─────────────────────────────────────────────┘
```

## 各层职责

### HTTP Handler

- **单一职责**：解析请求、调用 UseCase、返回响应
- 使用 Pydantic `BaseModel` 进行请求体验证（仅限 HTTP 边界）
- 不包含任何领域逻辑
- 通过 `make_xxx_router()` 工厂函数对外暴露

```python
@router.post("", status_code=201)
async def create_note(body: CreateNoteBody) -> JSONResponse:
    note = create_use_case.execute(CreateNoteInput(title=body.title, body=body.body))
    return JSONResponse({"id": note.id, "title": note.title, "body": note.body}, status_code=201)
```

### UseCase

- **单一职责**：实现一条业务规则
- 只有一个方法：`execute(input_: XxxInput) -> XxxOutput`
- 不导入 `fastapi`，不导入 `sqlalchemy`
- 不调用其他 UseCase
- 可单独使用 `InMemoryRepository` 进行测试

### RepositoryInterface

- 定义为 ABC — UseCase 只依赖接口，不依赖具体实现
- InMemory 版本和 SQLAlchemy 版本实现同一接口
- 标准方法：`find_all`、`find_by_id`、`save`、`update`、`delete`、`count`

### ConcreteRepository

- 使用 SQLAlchemy Core（非 ORM），配合参数化查询
- 通过 `SqlAlchemyQueryExecutor` 执行查询
- 表结构：示例应用使用集中式的 `src/example/schema.py`；新项目可在各领域的 `sqlalchemy_repository.py` 中定义 `ensure_schema()`，并在 `create_app()` 中逐一调用

## Middleware 栈

请求从最外层到最内层依次经过各 middleware：

```
BearerTokenMiddleware        身份验证（Bearer Token）
ApiKeyAuthMiddleware         身份验证（API Key）
CORSMiddleware               跨域资源共享
ThrottleMiddleware           限流（固定窗口）
RequestSizeLimitMiddleware   请求体大小限制
RequestLoggingMiddleware     结构化请求日志（structlog）
RequestIdMiddleware          X-Request-ID 生成与传播
SecurityHeadersMiddleware    安全响应头
ErrorHandlerMiddleware       异常 → RFC 9457 Problem Details
```

## 依赖注入

FastAPI 的 `Depends` 仅在 HTTP 边界使用。UseCase 和 repository 通过 `app.py` 中的构造函数注入进行组装。

```python
# app.py — 组装示例
note_repo = SqlAlchemyNoteRepository(executor)
app.include_router(make_note_router(
    list_use_case=ListNotesUseCase(note_repo),
    create_use_case=CreateNoteUseCase(note_repo),
    ...
))
```

## 领域包结构

```
src/example/<domain>/
  __init__.py
  entity.py              — @dataclass(frozen=True, slots=True)
  repository.py          — ABC + InMemory 实现
  exceptions.py          — XxxNotFoundException + ExceptionHandler
  use_case.py            — 5 个 UseCase + Input/Output DTO
  handler.py             — FastAPI router 工厂
  sqlalchemy_repository.py — SQL 后端实现
```
