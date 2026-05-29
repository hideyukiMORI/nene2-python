# Referência dos módulos do framework

API pública do pacote `nene2`.

---

## nene2.http

### `PaginationQueryParser`

Faz parse dos parâmetros de query `limit` e `offset`.

**FastAPI Depends (recomendado)**:

```python
from typing import Annotated
from fastapi import Depends
from nene2.http import PaginationQueryParser

@router.get("/items")
def list_items(pagination: Annotated[PaginationQueryParser, Depends()]) -> JSONResponse:
    result = use_case.execute(pagination.limit, pagination.offset)
```

**Legado (baseado em Request)**:

```python
from nene2.http import PaginationQueryParser

pagination = PaginationQueryParser.parse(request)
# pagination.limit  → int (máx 100, padrão 20)
# pagination.offset → int (padrão 0)
```

### `PaginationResponse`

Encapsula um conjunto de resultados paginados.

```python
from nene2.http import PaginationResponse

body = PaginationResponse(items=[...], limit=20, offset=0, total=42).to_dict()
# → {"items": [...], "limit": 20, "offset": 0, "total": 42}
```

### `problem_details_response()`

Gera uma resposta Problem Details RFC 9457.

```python
from nene2.http import problem_details_response

return problem_details_response("not-found", "Not Found", 404, "Note 42 not found.")
```

### `PaginationQuery`

Dataclass retornado por `PaginationQueryParser.parse()`. Contém `limit: int` e `offset: int`.

### `HealthCheckProtocol` / `HealthStatus`

Contrato e tipo de resultado para health checks da aplicação.

```python
from nene2.http import HealthCheckProtocol, HealthStatus

class MyHealthCheck:
    def check(self) -> HealthStatus:
        return HealthStatus(status="ok")
```

Campos de `HealthStatus`: `status: str` (`"ok"` ou `"error"`), `checks: dict[str, str]`.
A propriedade `is_healthy` retorna `True` quando `status == "ok"`.

### ETag e requisições condicionais

```python
from nene2.http import check_not_modified, check_precondition, generate_etag

etag = generate_etag({"id": 1, "title": "Hello"})
# Retorna 304 quando If-None-Match corresponde (GET)
check_not_modified(request, etag)
# Retorna 412 quando If-Match não corresponde (PUT/PATCH/DELETE)
check_precondition(request, etag)
```

### Helpers de parâmetros de query

Parsers tipados para padrões comuns de query (levantam `ValidationException` em entrada inválida):

```python
from nene2.http import query_array, query_bool, query_comma_separated, query_int, query_string

limit = query_int(request, "limit", default=20, minimum=1, maximum=100)
tags = query_comma_separated(request, "tags", max_items=10)
```

### `RequestScopedContext[T]`

Holder de valor com escopo de requisição para injeção de dependências (veja [lifespan-and-app-state](../how-to/lifespan-and-app-state.md)).

### `PaginationDep`

Alias `Depends()` do FastAPI para `PaginationQueryParser` — preferível ao parse manual.

---

## nene2.use_case

### `UseCaseProtocol[I, O]`

Contrato estrutural para UseCases síncronos.

```python
from nene2.use_case import UseCaseProtocol

class MyUseCase:
    def execute(self, input_: MyInput) -> MyOutput: ...

assert isinstance(MyUseCase(), UseCaseProtocol)
```

### `AsyncUseCaseProtocol[I, O]`

Contrato estrutural para UseCases async.

```python
from nene2.use_case import AsyncUseCaseProtocol

class MyAsyncUseCase:
    async def execute(self, input_: MyInput) -> MyOutput: ...

assert isinstance(MyAsyncUseCase(), AsyncUseCaseProtocol)
```

> **Nota**: verificações `isinstance` verificam apenas a presença de atributos. A distinção async/sync é aplicada estaticamente pelo `mypy --strict`.

---

## nene2.config

### `AppSettings`

Classe Pydantic Settings — lê de variáveis de ambiente e `.env`.

```python
from nene2.config import AppSettings

cfg = AppSettings()                                   # do ambiente
cfg_test = AppSettings(throttle_enabled=False)        # sobrescrever para testes
```

Veja a [Referência de configuração](configuration.md) para todos os campos.

---

## nene2.middleware

### `ErrorHandlerMiddleware`

Captura todas as exceções não tratadas e as converte em respostas Problem Details.
Registre handlers de exceção de domínio via `DomainExceptionHandlerProtocol`.

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

# Registro — passe como lista domain_handlers:
app.add_middleware(
    ErrorHandlerMiddleware,
    debug=settings.app_debug,
    domain_handlers=[NoteNotFoundExceptionHandler()],
)
```

`DomainExceptionHandlerProtocol` requer dois métodos:

| Método | Assinatura | Propósito |
|---|---|---|
| `handles` | `(exc: Exception) -> bool` | Retorne `True` se este handler possui a exceção |
| `handle` | `(exc: Exception) -> Response` | Converta a exceção em uma resposta HTTP |

### Outros middlewares

| Classe | Módulo | Papel |
|---|---|---|
| `SecurityHeadersMiddleware` | `nene2.middleware.security_headers` | Adicionar headers de segurança às respostas |
| `RequestIdMiddleware` | `nene2.middleware.request_id` | Gerar / propagar `X-Request-ID` |
| `RequestLoggingMiddleware` | `nene2.middleware.request_logging` | Logging estruturado de requisições / respostas |
| `RequestSizeLimitMiddleware` | `nene2.middleware.request_size_limit` | Rejeitar bodies de requisição muito grandes |
| `ThrottleMiddleware` | `nene2.middleware.throttle` | Rate limiting de janela fixa por IP |

#### Argumentos de `add_middleware`

O Starlette aplica middleware em **ordem inversa ao registro** — o último registrado se torna a camada mais externa. Registre `ErrorHandlerMiddleware` primeiro para capturar todas as exceções de todos os outros middlewares.

| Middleware | Argumentos keyword | Padrão |
|---|---|---|
| `ErrorHandlerMiddleware` | `debug: bool`, `domain_handlers: list[DomainExceptionHandlerProtocol] \| None` | `False`, `None` |
| `SecurityHeadersMiddleware` | *(nenhum)* | — |
| `RequestIdMiddleware` | *(nenhum)* | — |
| `RequestLoggingMiddleware` | *(nenhum)* | — |
| `RequestSizeLimitMiddleware` | `max_bytes: int` | `1_048_576` (1 MiB) |
| `ThrottleMiddleware` | `limit: int`, `window: int` | `60`, `60` |

`ThrottleMiddleware` não tem flag `enabled` — use `if settings.throttle_enabled:` para desabilitá-lo.

> **Nota — spoofing de `X-Forwarded-For`**: A chave de rate limit é derivada da primeira entrada do header `X-Forwarded-For`, que clientes podem falsificar. Em produção, sempre coloque a aplicação atrás de um reverse proxy confiável (nginx, Caddy, AWS ALB, etc.) que reescreva `X-Forwarded-For` antes de a requisição chegar ao app. Veja [ADR-0006](../adr/0006-rate-limiting.md) para detalhes.

#### Ordem completa de registro com middlewares opcionais

```python
# Ordem de registro: mais interno primeiro, mais externo por último.
# O Starlette executa em ordem inversa — o último registrado envolve todos os outros.
app.add_middleware(ErrorHandlerMiddleware, debug=settings.app_debug, domain_handlers=[...])
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_body_size)
if settings.throttle_enabled:
    app.add_middleware(ThrottleMiddleware, limit=settings.throttle_limit, window=settings.throttle_window)
# Middleware de auth — registrado antes do CORS para ficar dentro da camada CORS
if settings.bearer_token_enabled:
    app.add_middleware(BearerTokenMiddleware, verifier=LocalTokenVerifier(settings.bearer_tokens))
if settings.api_key_enabled:
    app.add_middleware(ApiKeyAuthMiddleware, verifier=LocalTokenVerifier(settings.api_keys))
# CORS deve ser a camada mais externa — registre por último.
# Requisições de preflight OPTIONS devem chegar ao CORSMiddleware antes de qualquer verificação de auth.
# Se CORSMiddleware for registrado antes do middleware de auth, a camada de auth se torna
# mais externa e retorna 401 no preflight, quebrando CORS para todos os navegadores.
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
```

> **Regra CORS + Auth**: Sempre registre `CORSMiddleware` *após* qualquer middleware de auth.
> Na ordem inversa do Starlette, "último registrado = mais externo" significa que CORS envolve auth,
> então requisições de preflight do navegador (`OPTIONS`) são tratadas antes da autenticação.

### `setup_middlewares()`

Registra a pilha completa de middleware do nene2 na ordem LIFO correta (incluindo CORS opcional).
Prefira isso a chamadas manuais de `add_middleware` quando não precisar de middleware customizado.

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

Veja o [how-to do middleware-stack](../how-to/middleware-stack.md).

### `SimpleDomainHandler`

Helper para construir `DomainExceptionHandlerProtocol` a partir de um tipo de exceção e código de status.

### Armazenamento de rate limit

| Símbolo | Papel |
|---|---|
| `RateLimitStorageProtocol` | Armazenamento plugável para contadores de throttle |
| `InMemoryRateLimitStorage` | Implementação padrão em processo |
| `ThrottleMiddleware` | Aceita `storage=` opcional para backends customizados |

---

## nene2.auth

### `LocalTokenVerifier`

Verifica tokens contra uma lista estática usando `secrets.compare_digest`.

```python
from nene2.auth import LocalTokenVerifier

verifier = LocalTokenVerifier(["token-a", "token-b"])
verifier.verify("token-a")  # True
verifier.verify("wrong")    # False
```

### `TokenVerifierProtocol` / `TokenIssuerProtocol`

Contratos estruturais para verificadores e emissores customizados (ex: JWT).

### `TokenVerificationException`

Lance isso a partir de um verificador para sinalizar um token inválido.
`BearerTokenMiddleware` o mapeia para `401 Unauthorized`.

### `CompositeAuthMiddleware`

Regras de prefixo de caminho para auth mista (ex: Bearer em `/api/*`, API Key em `/internal/*`).

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

Helpers de desenvolvimento para tokens bearer assinados com HMAC (veja rotas protegidas em `src/example/`).

### `make_require_auth()`

Factory `Depends()` do FastAPI que retorna 401 Problem Details quando headers de auth estão ausentes.

---

## nene2.database

### `SqlAlchemyQueryExecutor`

Executa SQL parametrizado via SQLAlchemy Core.

```python
from nene2.database import SqlAlchemyQueryExecutor

executor = SqlAlchemyQueryExecutor(engine)
rows = executor.fetch_all("SELECT * FROM notes WHERE id = :id", {"id": 1})
executor.write("INSERT INTO notes (title, body) VALUES (:t, :b)", {"t": "t", "b": "b"})
```

#### Valor de retorno de `write()`

`write()` retorna um `int` cujo significado depende da operação SQL:

| Operação | Valor de retorno |
|---|---|
| `INSERT` com `AUTOINCREMENT` / `SERIAL` | `lastrowid` — chave primária da nova linha (sempre > 0) |
| `INSERT` sem auto-PK, ou `INSERT` multi-linha | `rowcount` — número de linhas inseridas |
| `UPDATE` / `DELETE` | `rowcount` — linhas afetadas (0 se nada correspondeu) |

Use `lastrowid` para reconstruir a entidade após um INSERT de linha única:

```python
new_id = executor.write("INSERT INTO notes (title) VALUES (:title)", {"title": "Hello"})
return Note(id=new_id, title="Hello")
```

Use `rowcount` para detectar uma linha ausente em UPDATE / DELETE:

```python
affected = executor.write("UPDATE notes SET title=:title WHERE id=:id", {"title": t, "id": pk})
if affected == 0:
    raise NoteNotFoundException(pk)
```

### `SqlAlchemyTransactionManager`

Gerencia transações. Prefira `transactional()` a `begin/commit/rollback` manual.

```python
from nene2.database import SqlAlchemyTransactionManager

mgr = SqlAlchemyTransactionManager(engine)

result = mgr.transactional(
    lambda ex: ex.fetch_one("SELECT COUNT(*) AS cnt FROM notes")
)
```

#### Combinando `transactional()` com o padrão Repository

Quando um UseCase precisa realizar múltiplas escritas atomicamente, defina variantes `_in_tx` na interface do repository que aceitam um `executor` explícito. O UseCase passa o executor vinculado à transação do callback para cada método `_in_tx`.

**Interface do Repository:**

```python
from nene2.database import DatabaseQueryExecutorInterface
from abc import ABC, abstractmethod

class AccountRepositoryInterface(ABC):
    # Métodos padrão — usam self._executor (auto-commit)
    @abstractmethod
    def find_by_id(self, account_id: int) -> Account | None: ...

    # variantes _in_tx — chame apenas dentro de um callback transactional()
    @abstractmethod
    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None: ...

    @abstractmethod
    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta: int
    ) -> None: ...
```

**UseCase (exemplo de transferência atômica):**

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

`transactional()` usa `engine.begin()` internamente — qualquer exceção dentro do callback dispara um rollback automático.

**Testando com InMemory:** Implemente `DatabaseTransactionManagerInterface` com um executor no-op que chama o callback diretamente. Os métodos `_in_tx` no repository InMemory ignoram o executor e operam no store em memória.

### `DatabaseHealthCheck`

Implementa `HealthCheckProtocol` — verifica a conexão com o banco de dados e retorna um `HealthStatus`.

```python
from nene2.database import DatabaseHealthCheck
from nene2.http import HealthStatus

health = DatabaseHealthCheck(engine)
status: HealthStatus = health.check()
# status.status → "ok" ou "error"
# status.checks → {"db": "ok"} ou {"db": "error: <message>"}
```

### `DatabaseConnectionException`

Levantada por `DatabaseHealthCheck` ou operações de repository quando o banco de dados está inacessível.

---

## nene2.mcp

### `LocalMcpServer`

Encapsula FastMCP — registra funções UseCase como ferramentas MCP.

```python
from nene2.mcp import LocalMcpServer

server = LocalMcpServer("my-server", instructions="...")

@server.tool("List all notes.")
def list_notes(limit: int = 20, offset: int = 0) -> list[dict]: ...

server.run(transport="stdio")
```

### `HttpxMcpClient`

Cliente HTTP para chamar uma API nene2 a partir de handlers de ferramentas MCP.

```python
from nene2.mcp import HttpxMcpClient

client = HttpxMcpClient("bearer-token")
response = client.get("http://localhost:8080", "/notes")
response.is_successful()   # True
response.body              # str — texto bruto da resposta
response.status_code       # int
response.request_id()      # str | None — valor do header X-Request-ID
```

### `McpHttpResponse`

Tipo de retorno dos métodos de `HttpxMcpClient`.

Campos: `status_code: int`, `headers: dict[str, str]`, `body: str` (texto bruto da resposta).

Métodos:
- `is_successful() -> bool` — `True` quando `200 ≤ status_code < 300`
- `request_id() -> str | None` — retorna o valor do header de resposta `X-Request-ID`, ou `None`

### `McpHttpClientProtocol`

Contrato estrutural para clientes HTTP MCP customizados. Implemente `get()`, `post()`, `put()`, `delete()` retornando `McpHttpResponse`, e `has_authentication() -> bool`.

---

## nene2.log

### `setup_logging()`

Inicializa o structlog. Alterna entre ConsoleRenderer (local) e JSON (produção).

```python
from nene2.log import setup_logging

setup_logging(app_env="production")  # renderer JSON
setup_logging(app_env="local")       # renderer Console
```

---

## nene2.validation

### `ValidationException` / `ValidationError`

Levante `ValidationException` na fronteira HTTP para retornar `422 Unprocessable Entity`.

```python
from nene2.validation.exceptions import ValidationError, ValidationException

errors = [ValidationError("body", "Body must not be empty.", "required")]
raise ValidationException(errors)
```

---

## nene2.cache

### `TtlCache[V]`

Cache em memória thread-safe com expiração TTL por chave. Use para chaves de idempotência, lookups de curta duração, ou adjuntos de rate limit.

```python
from nene2.cache import TtlCache

cache: TtlCache[str] = TtlCache(ttl_seconds=60.0)
cache.set("key", "value")
cache.get("key")  # str | None
```

Veja o [how-to de lifespan-and-app-state](../how-to/lifespan-and-app-state.md) para conexão com `app.state`.

---

## nene2.security

### `verify_hmac_signature()`

Verificação HMAC segura contra timing attacks para endpoints de webhook.

```python
from nene2.security import verify_hmac_signature

if not verify_hmac_signature(body, signature_header, secret.get_secret_value()):
    return problem_details_response("unauthorized", "Unauthorized", 401, "Invalid signature.")
```

Veja o [how-to de webhook](../how-to/webhook.md).
