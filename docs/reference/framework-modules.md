# Framework modules reference

Public API of the `nene2` package.

---

## nene2.http

### `PaginationQueryParser`

Parses `limit` and `offset` query parameters.

```python
from nene2.http import PaginationQueryParser

pagination = PaginationQueryParser.parse(request)
# pagination.limit  → int (max 100, default 20)
# pagination.offset → int (default 0)
```

### `PaginationResponse`

Wraps a paginated result set.

```python
from nene2.http import PaginationResponse

body = PaginationResponse(items=[...], limit=20, offset=0, total=42).to_dict()
# → {"items": [...], "limit": 20, "offset": 0, "total": 42}
```

### `problem_details_response()`

Generates an RFC 9457 Problem Details response.

```python
from nene2.http import problem_details_response

return problem_details_response("not-found", "Not Found", 404, "Note 42 not found.")
```

### `PaginationQuery`

Dataclass returned by `PaginationQueryParser.parse()`. Contains `limit: int` and `offset: int`.

### `HealthCheckProtocol` / `HealthStatus`

Contract and result type for application health checks.

```python
from nene2.http import HealthCheckProtocol, HealthStatus

class MyHealthCheck:
    def check(self) -> HealthStatus:
        return HealthStatus(status="ok")
```

`HealthStatus` fields: `status: str` (`"ok"` or `"error"`), `checks: dict[str, str]`.
`is_healthy` property returns `True` when `status == "ok"`.

---

## nene2.use_case

### `UseCaseProtocol[I, O]`

Structural contract for synchronous UseCases.

```python
from nene2.use_case import UseCaseProtocol

class MyUseCase:
    def execute(self, input_: MyInput) -> MyOutput: ...

assert isinstance(MyUseCase(), UseCaseProtocol)
```

### `AsyncUseCaseProtocol[I, O]`

Structural contract for async UseCases.

```python
from nene2.use_case import AsyncUseCaseProtocol

class MyAsyncUseCase:
    async def execute(self, input_: MyInput) -> MyOutput: ...

assert isinstance(MyAsyncUseCase(), AsyncUseCaseProtocol)
```

> **Note**: `isinstance` checks attribute presence only. The async/sync distinction is enforced statically by `mypy --strict`.

---

## nene2.config

### `AppSettings`

Pydantic Settings class — reads from environment variables and `.env`.

```python
from nene2.config import AppSettings

cfg = AppSettings()                                   # from environment
cfg_test = AppSettings(throttle_enabled=False)        # override for tests
```

See [Configuration reference](configuration.md) for all fields.

---

## nene2.middleware

### `ErrorHandlerMiddleware`

Catches all unhandled exceptions and converts them to Problem Details responses.
Register domain exception handlers via `DomainExceptionHandlerProtocol`.

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

# Registration — pass as domain_handlers list:
app.add_middleware(
    ErrorHandlerMiddleware,
    debug=settings.app_debug,
    domain_handlers=[NoteNotFoundExceptionHandler()],
)
```

`DomainExceptionHandlerProtocol` requires two methods:

| Method | Signature | Purpose |
|---|---|---|
| `handles` | `(exc: Exception) -> bool` | Return `True` if this handler owns the exception |
| `handle` | `(exc: Exception) -> Response` | Convert exception to an HTTP response |

### Other middleware

| Class | Module | Role |
|---|---|---|
| `SecurityHeadersMiddleware` | `nene2.middleware.security_headers` | Add security response headers |
| `RequestIdMiddleware` | `nene2.middleware.request_id` | Generate / propagate `X-Request-ID` |
| `RequestLoggingMiddleware` | `nene2.middleware.request_logging` | Structured request / response logging |
| `RequestSizeLimitMiddleware` | `nene2.middleware.request_size_limit` | Reject oversized request bodies |
| `ThrottleMiddleware` | `nene2.middleware.throttle` | Fixed-window rate limiting per IP |

#### `add_middleware` arguments

Starlette applies middleware in **reverse registration order** — the last registered becomes the outermost layer. Register `ErrorHandlerMiddleware` first so it catches all exceptions from every other middleware.

| Middleware | Keyword arguments | Default |
|---|---|---|
| `ErrorHandlerMiddleware` | `debug: bool`, `domain_handlers: list[DomainExceptionHandlerProtocol] \| None` | `False`, `None` |
| `SecurityHeadersMiddleware` | *(none)* | — |
| `RequestIdMiddleware` | *(none)* | — |
| `RequestLoggingMiddleware` | *(none)* | — |
| `RequestSizeLimitMiddleware` | `max_bytes: int` | `1_048_576` (1 MiB) |
| `ThrottleMiddleware` | `limit: int`, `window: int` | `60`, `60` |

`ThrottleMiddleware` has no `enabled` flag — wrap with `if settings.throttle_enabled:` to disable it.

#### Full registration order with optional middleware

```python
# Registration order: innermost first, outermost last.
# Starlette executes in reverse — the last registered wraps all others.
app.add_middleware(ErrorHandlerMiddleware, debug=settings.app_debug, domain_handlers=[...])
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_body_size)
if settings.throttle_enabled:
    app.add_middleware(ThrottleMiddleware, limit=settings.throttle_limit, window=settings.throttle_window)
# Auth middleware — registered before CORS so it sits inside the CORS layer
if settings.bearer_token_enabled:
    app.add_middleware(BearerTokenMiddleware, verifier=LocalTokenVerifier(settings.bearer_tokens))
if settings.api_key_enabled:
    app.add_middleware(ApiKeyAuthMiddleware, verifier=LocalTokenVerifier(settings.api_keys))
# CORS must be the outermost layer — register it last.
# OPTIONS preflight requests must reach CORSMiddleware before any auth check.
# If CORSMiddleware is registered before auth middleware, the auth layer becomes
# outermost and returns 401 on preflight, breaking CORS for all browsers.
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
```

> **CORS + Auth rule**: Always register `CORSMiddleware` *after* any auth middleware.
> In Starlette's reverse order, "last registered = outermost" means CORS wraps auth,
> so browser preflight (`OPTIONS`) requests are handled before authentication.

---

## nene2.auth

### `LocalTokenVerifier`

Verifies tokens against a static list using `secrets.compare_digest`.

```python
from nene2.auth import LocalTokenVerifier

verifier = LocalTokenVerifier(["token-a", "token-b"])
verifier.verify("token-a")  # True
verifier.verify("wrong")    # False
```

### `TokenVerifierProtocol` / `TokenIssuerProtocol`

Structural contracts for custom verifiers and issuers (e.g. JWT).

### `TokenVerificationException`

Raise this from a verifier to signal an invalid token.
`BearerTokenMiddleware` maps it to `401 Unauthorized`.

---

## nene2.database

### `SqlAlchemyQueryExecutor`

Executes parameterised SQL via SQLAlchemy Core.

```python
from nene2.database import SqlAlchemyQueryExecutor

executor = SqlAlchemyQueryExecutor(engine)
rows = executor.fetch_all("SELECT * FROM notes WHERE id = :id", {"id": 1})
executor.write("INSERT INTO notes (title, body) VALUES (:t, :b)", {"t": "t", "b": "b"})
```

#### `write()` return value

`write()` returns an `int` whose meaning depends on the SQL operation:

| Operation | Return value |
|---|---|
| `INSERT` with `AUTOINCREMENT` / `SERIAL` | `lastrowid` — the new row's primary key (always > 0) |
| `INSERT` without auto-PK, or multi-row `INSERT` | `rowcount` — number of rows inserted |
| `UPDATE` / `DELETE` | `rowcount` — rows affected (0 if nothing matched) |

Use `lastrowid` to reconstruct the entity after a single-row INSERT:

```python
new_id = executor.write("INSERT INTO notes (title) VALUES (:title)", {"title": "Hello"})
return Note(id=new_id, title="Hello")
```

Use `rowcount` to detect a missing row on UPDATE / DELETE:

```python
affected = executor.write("UPDATE notes SET title=:title WHERE id=:id", {"title": t, "id": pk})
if affected == 0:
    raise NoteNotFoundException(pk)
```

### `SqlAlchemyTransactionManager`

Manages transactions. Prefer `transactional()` over manual `begin/commit/rollback`.

```python
from nene2.database import SqlAlchemyTransactionManager

mgr = SqlAlchemyTransactionManager(engine)

result = mgr.transactional(
    lambda ex: ex.fetch_one("SELECT COUNT(*) AS cnt FROM notes")
)
```

#### Combining `transactional()` with the Repository pattern

When a UseCase needs to perform multiple writes atomically, define `_in_tx` variants on the repository interface that accept an explicit `executor`. The UseCase passes the transaction-bound executor from the callback to each `_in_tx` method.

**Repository interface:**

```python
from nene2.database import DatabaseQueryExecutorInterface
from abc import ABC, abstractmethod

class AccountRepositoryInterface(ABC):
    # Standard methods — use self._executor (auto-commit)
    @abstractmethod
    def find_by_id(self, account_id: int) -> Account | None: ...

    # _in_tx variants — call only inside a transactional() callback
    @abstractmethod
    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None: ...

    @abstractmethod
    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta: int
    ) -> None: ...
```

**UseCase (atomic transfer example):**

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

`transactional()` uses `engine.begin()` internally — any exception inside the callback triggers an automatic rollback.

**Testing with InMemory:** Implement `DatabaseTransactionManagerInterface` with a no-op executor that calls the callback directly. The `_in_tx` methods on the InMemory repository ignore the executor and operate on their in-memory store.

### `DatabaseHealthCheck`

Implements `HealthCheckProtocol` — verifies the database connection and returns a `HealthStatus`.

```python
from nene2.database import DatabaseHealthCheck
from nene2.http import HealthStatus

health = DatabaseHealthCheck(engine)
status: HealthStatus = health.check()
# status.status → "ok" or "error"
# status.checks → {"db": "ok"} or {"db": "error: <message>"}
```

### `DatabaseConnectionException`

Raised by `DatabaseHealthCheck` or repository operations when the database is unreachable.

---

## nene2.mcp

### `LocalMcpServer`

Wraps FastMCP — registers UseCase functions as MCP tools.

```python
from nene2.mcp import LocalMcpServer

server = LocalMcpServer("my-server", instructions="...")

@server.tool("List all notes.")
def list_notes(limit: int = 20, offset: int = 0) -> list[dict]: ...

server.run(transport="stdio")
```

### `HttpxMcpClient`

HTTP client for calling a nene2 API from MCP tool handlers.

```python
from nene2.mcp import HttpxMcpClient

client = HttpxMcpClient("bearer-token")
response = client.get("http://localhost:8080", "/notes")
response.is_successful()   # True
response.body              # str — raw response text
response.status_code       # int
response.request_id()      # str | None — value of X-Request-ID header
```

### `McpHttpResponse`

Return type of `HttpxMcpClient` methods.

Fields: `status_code: int`, `headers: dict[str, str]`, `body: str` (raw response text).

Methods:
- `is_successful() -> bool` — `True` when `200 ≤ status_code < 300`
- `request_id() -> str | None` — returns the `X-Request-ID` response header value, or `None`

### `McpHttpClientProtocol`

Structural contract for custom MCP HTTP clients. Implement `get()`, `post()`, `put()`, `delete()` returning `McpHttpResponse`, and `has_authentication() -> bool`.

---

## nene2.log

### `setup_logging()`

Initialises structlog. Switches between ConsoleRenderer (local) and JSON (production).

```python
from nene2.log import setup_logging

setup_logging(app_env="production")  # JSON renderer
setup_logging(app_env="local")       # Console renderer
```

---

## nene2.validation

### `ValidationException` / `ValidationError`

Raise `ValidationException` at the HTTP boundary to return `422 Unprocessable Entity`.

```python
from nene2.validation.exceptions import ValidationError, ValidationException

errors = [ValidationError("body", "Body must not be empty.", "required")]
raise ValidationException(errors)
```
