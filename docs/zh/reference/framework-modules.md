# 框架模块参考

`nene2` 包的公开 API。

---

## nene2.http

### `PaginationQueryParser`

解析 `limit` 和 `offset` 查询参数。

**FastAPI Depends（推荐）**：

```python
from typing import Annotated
from fastapi import Depends
from nene2.http import PaginationQueryParser

@router.get("/items")
def list_items(pagination: Annotated[PaginationQueryParser, Depends()]) -> JSONResponse:
    result = use_case.execute(pagination.limit, pagination.offset)
```

**旧版（基于 Request）**：

```python
from nene2.http import PaginationQueryParser

pagination = PaginationQueryParser.parse(request)
# pagination.limit  → int（最大 100，默认 20）
# pagination.offset → int（默认 0）
```

### `PaginationResponse`

包装分页结果集。

```python
from nene2.http import PaginationResponse

body = PaginationResponse(items=[...], limit=20, offset=0, total=42).to_dict()
# → {"items": [...], "limit": 20, "offset": 0, "total": 42}
```

### `problem_details_response()`

生成符合 RFC 9457 规范的 Problem Details 响应。

```python
from nene2.http import problem_details_response

return problem_details_response("not-found", "Not Found", 404, "Note 42 not found.")
```

### `PaginationQuery`

`PaginationQueryParser.parse()` 返回的 dataclass，包含 `limit: int` 和 `offset: int`。

### `HealthCheckProtocol` / `HealthStatus`

应用健康检查的契约和结果类型。

```python
from nene2.http import HealthCheckProtocol, HealthStatus

class MyHealthCheck:
    def check(self) -> HealthStatus:
        return HealthStatus(status="ok")
```

`HealthStatus` 字段：`status: str`（`"ok"` 或 `"error"`）、`checks: dict[str, str]`。`is_healthy` 属性在 `status == "ok"` 时返回 `True`。

### ETag 与条件请求

```python
from nene2.http import check_not_modified, check_precondition, generate_etag

etag = generate_etag({"id": 1, "title": "Hello"})
# If-None-Match 匹配时返回 304（GET）
check_not_modified(request, etag)
# If-Match 不匹配时返回 412（PUT/PATCH/DELETE）
check_precondition(request, etag)
```

### 查询参数辅助函数

常见查询模式的类型化解析器（输入无效时抛出 `ValidationException`）：

```python
from nene2.http import query_array, query_bool, query_comma_separated, query_int, query_string

limit = query_int(request, "limit", default=20, minimum=1, maximum=100)
tags = query_comma_separated(request, "tags", max_items=10)
```

### `RequestScopedContext[T]`

用于依赖注入的请求作用域值容器（参见 [lifespan-and-app-state](../how-to/lifespan-and-app-state.md)）。

### `PaginationDep`

`PaginationQueryParser` 的 FastAPI `Depends()` 别名 — 优先于手动解析。

---

## nene2.use_case

### `UseCaseProtocol[I, O]`

同步 UseCase 的结构化契约。

```python
from nene2.use_case import UseCaseProtocol

class MyUseCase:
    def execute(self, input_: MyInput) -> MyOutput: ...

assert isinstance(MyUseCase(), UseCaseProtocol)
```

### `AsyncUseCaseProtocol[I, O]`

异步 UseCase 的结构化契约。

```python
from nene2.use_case import AsyncUseCaseProtocol

class MyAsyncUseCase:
    async def execute(self, input_: MyInput) -> MyOutput: ...

assert isinstance(MyAsyncUseCase(), AsyncUseCaseProtocol)
```

> **注意**：`isinstance` 检查仅验证属性是否存在。async/sync 的区别由 `mypy --strict` 静态强制执行。

---

## nene2.config

### `AppSettings`

Pydantic Settings 类 — 从环境变量和 `.env` 读取配置。

```python
from nene2.config import AppSettings

cfg = AppSettings()                                   # 从环境变量读取
cfg_test = AppSettings(throttle_enabled=False)        # 测试时覆盖
```

所有字段请参阅 [配置参考](configuration.md)。

---

## nene2.middleware

### `ErrorHandlerMiddleware`

捕获所有未处理异常并转换为 Problem Details 响应。通过 `DomainExceptionHandlerProtocol` 注册领域异常处理器。

```python
from starlette.responses import Response
from nene2.http import problem_details_response
from nene2.middleware import ErrorHandlerMiddleware
from nene2.middleware.domain_exception import DomainExceptionHandlerProtocol

class NoteNotFoundExceptionHandler:
    def handles(self, exc: Exception) -> bool:
        return isinstance(exc, NoteNotFoundException)

    def handle(self, exc: Exception) -> Response:
        assert isinstance(exc, NoteNotFoundException)
        return problem_details_response("not-found", "Not Found", 404, str(exc))

# 注册 — 以 domain_handlers 列表传入：
app.add_middleware(
    ErrorHandlerMiddleware,
    debug=settings.app_debug,
    domain_handlers=[NoteNotFoundExceptionHandler()],
)
```

`DomainExceptionHandlerProtocol` 要求两个方法：

| 方法 | 签名 | 用途 |
|---|---|---|
| `handles` | `(exc: Exception) -> bool` | 若此处理器负责该异常则返回 `True` |
| `handle` | `(exc: Exception) -> Response` | 将异常转换为 HTTP 响应 |

### 其他 middleware

| 类 | 模块 | 职责 |
|---|---|---|
| `SecurityHeadersMiddleware` | `nene2.middleware.security_headers` | 添加安全响应头 |
| `RequestIdMiddleware` | `nene2.middleware.request_id` | 生成/传播 `X-Request-ID` |
| `RequestLoggingMiddleware` | `nene2.middleware.request_logging` | 结构化请求/响应日志 |
| `RequestSizeLimitMiddleware` | `nene2.middleware.request_size_limit` | 拒绝超大请求体 |
| `ThrottleMiddleware` | `nene2.middleware.throttle` | 基于 IP 的固定窗口限流 |

#### `add_middleware` 参数

Starlette 以**注册顺序的逆序**应用 middleware — 最后注册的成为最外层。先注册 `ErrorHandlerMiddleware`，使其捕获所有其他 middleware 的异常。

| Middleware | 关键字参数 | 默认值 |
|---|---|---|
| `ErrorHandlerMiddleware` | `debug: bool`, `domain_handlers: list[DomainExceptionHandlerProtocol] \| None` | `False`, `None` |
| `SecurityHeadersMiddleware` | （无） | — |
| `RequestIdMiddleware` | （无） | — |
| `RequestLoggingMiddleware` | （无） | — |
| `RequestSizeLimitMiddleware` | `max_bytes: int` | `1_048_576`（1 MiB） |
| `ThrottleMiddleware` | `limit: int`, `window: int` | `60`, `60` |

`ThrottleMiddleware` 没有 `enabled` 标志 — 通过 `if settings.throttle_enabled:` 来禁用它。

> **注意 — `X-Forwarded-For` 欺骗**：限流键来自 `X-Forwarded-For` 头的第一个条目，客户端可以伪造。在生产环境中，请始终将应用置于可信任的反向代理（nginx、Caddy、AWS ALB 等）之后，在请求到达应用前重写 `X-Forwarded-For`。详见 [ADR-0006](../adr/0006-rate-limiting.md)。

#### 含可选 middleware 的完整注册顺序

```python
# 注册顺序：最内层优先，最外层最后。
# Starlette 以逆序执行 — 最后注册的包裹所有其他 middleware。
app.add_middleware(ErrorHandlerMiddleware, debug=settings.app_debug, domain_handlers=[...])
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_body_size)
if settings.throttle_enabled:
    app.add_middleware(ThrottleMiddleware, limit=settings.throttle_limit, window=settings.throttle_window)
# Auth middleware — 在 CORS 之前注册，使其位于 CORS 层内部
if settings.bearer_token_enabled:
    app.add_middleware(BearerTokenMiddleware, verifier=LocalTokenVerifier(settings.bearer_tokens))
if settings.api_key_enabled:
    app.add_middleware(ApiKeyAuthMiddleware, verifier=LocalTokenVerifier(settings.api_keys))
# CORS 必须是最外层 — 最后注册。
# OPTIONS 预检请求必须在任何认证检查之前到达 CORSMiddleware。
# 如果 CORSMiddleware 在 auth middleware 之前注册，auth 层将成为最外层，
# 对预检请求返回 401，导致所有浏览器的 CORS 失败。
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
```

> **CORS + Auth 规则**：始终在 auth middleware *之后*注册 `CORSMiddleware`。在 Starlette 的逆序中，"最后注册 = 最外层"意味着 CORS 包裹 auth，浏览器预检（`OPTIONS`）请求在认证之前得到处理。

### `setup_middlewares()`

以正确的 LIFO 顺序注册完整的 nene2 middleware 栈（含可选 CORS）。在不需要自定义 middleware 时，优先使用此函数而非手动 `add_middleware` 调用。

```python
from nene2.middleware import setup_middlewares

setup_middlewares(
    app,
    debug=settings.app_debug,
    domain_handlers=[NoteNotFoundExceptionHandler()],
    throttle_limit=settings.throttle_limit if settings.throttle_enabled else None,
    max_request_bytes=settings.max_body_size,
    cors_allowed_origins=settings.cors_origins if settings.cors_enabled else None,
)
```

参见 [middleware-stack 操作指南](../how-to/middleware-stack.md)。

### `SimpleDomainHandler`

从异常类型和状态码构建 `DomainExceptionHandlerProtocol` 的辅助工具。

### 限流存储

| 符号 | 职责 |
|---|---|
| `RateLimitStorageProtocol` | 可插拔的限流计数器存储 |
| `InMemoryRateLimitStorage` | 默认进程内实现 |
| `ThrottleMiddleware` | 接受可选的 `storage=` 参数支持自定义后端 |

---

## nene2.auth

### `LocalTokenVerifier`

使用 `secrets.compare_digest` 对静态列表验证 Token。

```python
from nene2.auth import LocalTokenVerifier

verifier = LocalTokenVerifier(["token-a", "token-b"])
verifier.verify("token-a")  # True
verifier.verify("wrong")    # False
```

### `TokenVerifierProtocol` / `TokenIssuerProtocol`

自定义 verifier 和 issuer（如 JWT）的结构化契约。

### `TokenVerificationException`

从 verifier 中抛出以表示 Token 无效。`BearerTokenMiddleware` 将其映射为 `401 Unauthorized`。

### `CompositeAuthMiddleware`

按路径前缀混合认证方式（例如 Bearer 用于 `/api/*`，API Key 用于 `/internal/*`）。

```python
from nene2.auth import CompositeAuthMiddleware, CompositeAuthRule, bearer_check, api_key_check

app.add_middleware(
    CompositeAuthMiddleware,
    rules=[
        CompositeAuthRule(prefix="/api", check=bearer_check(verifier)),
        CompositeAuthRule(prefix="/internal", check=api_key_check(verifier)),
    ],
)
```

### `LocalTokenIssuer` / `LocalBearerJwtVerifier`

用于 HMAC 签名 Bearer Token 的开发辅助工具（参见 `src/example/` 受保护路由）。

### `make_require_auth()`

FastAPI `Depends()` 工厂，当认证头缺失时返回 401 Problem Details。

---

## nene2.database

### `SqlAlchemyQueryExecutor`

通过 SQLAlchemy Core 执行参数化 SQL。

```python
from nene2.database import SqlAlchemyQueryExecutor

executor = SqlAlchemyQueryExecutor(engine)
rows = executor.fetch_all("SELECT * FROM notes WHERE id = :id", {"id": 1})
executor.write("INSERT INTO notes (title, body) VALUES (:t, :b)", {"t": "t", "b": "b"})
```

#### `write()` 的返回值

`write()` 返回 `int`，其含义取决于 SQL 操作：

| 操作 | 返回值 |
|---|---|
| 带 `AUTOINCREMENT` / `SERIAL` 的 `INSERT` | `lastrowid` — 新行主键（始终 > 0） |
| 无自增主键或多行 `INSERT` | `rowcount` — 插入的行数 |
| `UPDATE` / `DELETE` | `rowcount` — 受影响的行数（未匹配时为 0） |

使用 `lastrowid` 在单行 INSERT 后重建实体：

```python
new_id = executor.write("INSERT INTO notes (title) VALUES (:title)", {"title": "Hello"})
return Note(id=new_id, title="Hello")
```

使用 `rowcount` 检测 UPDATE / DELETE 时的缺失行：

```python
affected = executor.write("UPDATE notes SET title=:title WHERE id=:id", {"title": t, "id": pk})
if affected == 0:
    raise NoteNotFoundException(pk)
```

### `SqlAlchemyTransactionManager`

管理事务。优先使用 `transactional()` 而非手动 `begin/commit/rollback`。

```python
from nene2.database import SqlAlchemyTransactionManager

mgr = SqlAlchemyTransactionManager(engine)

result = mgr.transactional(
    lambda ex: ex.fetch_one("SELECT COUNT(*) AS cnt FROM notes")
)
```

#### 将 `transactional()` 与 Repository 模式结合

当 UseCase 需要原子地执行多次写入时，在 repository 接口上定义接受显式 `executor` 的 `_in_tx` 变体方法。UseCase 将事务绑定的 executor 从回调传入每个 `_in_tx` 方法。

**Repository 接口：**

```python
from nene2.database import DatabaseQueryExecutorInterface
from abc import ABC, abstractmethod

class AccountRepositoryInterface(ABC):
    # 标准方法 — 使用 self._executor（自动提交）
    @abstractmethod
    def find_by_id(self, account_id: int) -> Account | None: ...

    # _in_tx 变体 — 仅在 transactional() 回调内调用
    @abstractmethod
    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None: ...

    @abstractmethod
    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta: int
    ) -> None: ...
```

**UseCase（原子转账示例）：**

```python
from nene2.database import DatabaseQueryExecutorInterface, DatabaseTransactionManagerInterface

class TransferUseCase:
    def __init__(
        self,
        transaction_manager: DatabaseTransactionManagerInterface,
        account_repo: AccountRepositoryInterface,
        transfer_repo: TransferRepositoryInterface,
    ) -> None:
        self._tx = transaction_manager
        self._accounts = account_repo
        self._transfers = transfer_repo

    def execute(self, input_: TransferInput) -> Transfer:
        def _run(executor: DatabaseQueryExecutorInterface) -> Transfer:
            source = self._accounts.find_by_id_in_tx(executor, input_.from_account_id)
            if source is None:
                raise AccountNotFoundException(input_.from_account_id)
            if source.balance_cents < input_.amount_cents:
                raise InsufficientBalanceException(...)

            self._accounts.update_balance_in_tx(executor, input_.from_account_id, -input_.amount_cents)
            self._accounts.update_balance_in_tx(executor, input_.to_account_id, input_.amount_cents)
            return self._transfers.create_in_tx(executor, input_.from_account_id, input_.to_account_id, input_.amount_cents)

        return self._tx.transactional(_run)
```

`transactional()` 内部使用 `engine.begin()` — 回调内的任何异常都会触发自动回滚。

**使用 InMemory 测试：** 实现 `DatabaseTransactionManagerInterface`，使用无操作 executor 直接调用回调。InMemory repository 上的 `_in_tx` 方法忽略 executor，直接对内存存储操作。

### `DatabaseHealthCheck`

实现 `HealthCheckProtocol` — 验证数据库连接并返回 `HealthStatus`。

```python
from nene2.database import DatabaseHealthCheck
from nene2.http import HealthStatus

health = DatabaseHealthCheck(engine)
status: HealthStatus = health.check()
# status.status → "ok" 或 "error"
# status.checks → {"db": "ok"} 或 {"db": "error: <message>"}
```

### `DatabaseConnectionException`

当数据库不可达时，由 `DatabaseHealthCheck` 或 repository 操作抛出。

---

## nene2.mcp

### `LocalMcpServer`

封装 FastMCP — 将 UseCase 函数注册为 MCP 工具。

```python
from nene2.mcp import LocalMcpServer

server = LocalMcpServer("my-server", instructions="...")

@server.tool("List all notes.")
def list_notes(limit: int = 20, offset: int = 0) -> list[dict]: ...

server.run(transport="stdio")
```

### `HttpxMcpClient`

从 MCP 工具处理器调用 nene2 API 的 HTTP 客户端。

```python
from nene2.mcp import HttpxMcpClient

client = HttpxMcpClient("bearer-token")
response = client.get("http://localhost:8080", "/notes")
response.is_successful()   # True
response.body              # str — 原始响应文本
response.status_code       # int
response.request_id()      # str | None — X-Request-ID 头的值
```

### `McpHttpResponse`

`HttpxMcpClient` 方法的返回类型。

字段：`status_code: int`、`headers: dict[str, str]`、`body: str`（原始响应文本）。

方法：
- `is_successful() -> bool` — `200 ≤ status_code < 300` 时返回 `True`
- `request_id() -> str | None` — 返回 `X-Request-ID` 响应头的值，如不存在则返回 `None`

### `McpHttpClientProtocol`

自定义 MCP HTTP 客户端的结构化契约。实现 `get()`、`post()`、`put()`、`delete()`（返回 `McpHttpResponse`）和 `has_authentication() -> bool`。

---

## nene2.log

### `setup_logging()`

初始化 structlog。在本地环境使用 ConsoleRenderer，在生产环境使用 JSON 格式。

```python
from nene2.log import setup_logging

setup_logging(app_env="production")  # JSON 渲染器
setup_logging(app_env="local")       # 控制台渲染器
```

---

## nene2.validation

### `ValidationException` / `ValidationError`

在 HTTP 边界抛出 `ValidationException` 以返回 `422 Unprocessable Entity`。

```python
from nene2.validation.exceptions import ValidationError, ValidationException

errors = [ValidationError("body", "Body must not be empty.", "required")]
raise ValidationException(errors)
```

---

## nene2.cache

### `TtlCache[V]`

线程安全的内存缓存，支持按键 TTL 过期。适用于幂等性键、短期查询或限流辅助。

```python
from nene2.cache import TtlCache

cache: TtlCache[str] = TtlCache(ttl_seconds=60.0)
cache.set("key", "value")
cache.get("key")  # str | None
```

关于 `app.state` 的接入方式，参见 [lifespan-and-app-state 操作指南](../how-to/lifespan-and-app-state.md)。

---

## nene2.security

### `verify_hmac_signature()`

用于 Webhook endpoint 的防时序攻击 HMAC 验证。

```python
from nene2.security import verify_hmac_signature

if not verify_hmac_signature(body, signature_header, secret.get_secret_value()):
    return problem_details_response("unauthorized", "Unauthorized", 401, "Invalid signature.")
```

参见 [webhook 操作指南](../how-to/webhook.md)。
