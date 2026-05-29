# Framework-Modulreferenz

Öffentliche API des `nene2`-Pakets.

---

## nene2.http

### `PaginationQueryParser`

Parst `limit`- und `offset`-Query-Parameter.

**FastAPI Depends (empfohlen)**:

```python
from typing import Annotated
from fastapi import Depends
from nene2.http import PaginationQueryParser

@router.get("/items")
def list_items(pagination: Annotated[PaginationQueryParser, Depends()]) -> JSONResponse:
    result = use_case.execute(pagination.limit, pagination.offset)
```

**Legacy (Request-basiert)**:

```python
from nene2.http import PaginationQueryParser

pagination = PaginationQueryParser.parse(request)
# pagination.limit  → int (max 100, Standard 20)
# pagination.offset → int (Standard 0)
```

### `PaginationResponse`

Umschließt eine paginierte Ergebnismenge.

```python
from nene2.http import PaginationResponse

body = PaginationResponse(items=[...], limit=20, offset=0, total=42).to_dict()
# → {"items": [...], "limit": 20, "offset": 0, "total": 42}
```

### `problem_details_response()`

Generiert eine RFC-9457-Problem-Details-Antwort.

```python
from nene2.http import problem_details_response

return problem_details_response("not-found", "Not Found", 404, "Note 42 not found.")
```

### `PaginationQuery`

Dataclass, der von `PaginationQueryParser.parse()` zurückgegeben wird. Enthält `limit: int` und `offset: int`.

### `HealthCheckProtocol` / `HealthStatus`

Vertrag und Ergebnistyp für Anwendungs-Health-Checks.

```python
from nene2.http import HealthCheckProtocol, HealthStatus

class MyHealthCheck:
    def check(self) -> HealthStatus:
        return HealthStatus(status="ok")
```

`HealthStatus`-Felder: `status: str` (`"ok"` oder `"error"`), `checks: dict[str, str]`. Die `is_healthy`-Property gibt `True` zurück, wenn `status == "ok"`.

### ETag und bedingte Anfragen

```python
from nene2.http import check_not_modified, check_precondition, generate_etag

etag = generate_etag({"id": 1, "title": "Hello"})
# Gibt 304 zurück, wenn If-None-Match übereinstimmt (GET)
check_not_modified(request, etag)
# Gibt 412 zurück, wenn If-Match nicht übereinstimmt (PUT/PATCH/DELETE)
check_precondition(request, etag)
```

### Query-Parameter-Helfer

Typisierte Parser für gängige Query-Muster (lösen `ValidationException` bei ungültiger Eingabe aus):

```python
from nene2.http import query_array, query_bool, query_comma_separated, query_int, query_string

limit = query_int(request, "limit", default=20, minimum=1, maximum=100)
tags = query_comma_separated(request, "tags", max_items=10)
```

### `RequestScopedContext[T]`

Request-scoped Werthalter für Dependency Injection (siehe [lifespan-and-app-state](../how-to/lifespan-and-app-state.md)).

### `PaginationDep`

FastAPI-`Depends()`-Alias für `PaginationQueryParser` — gegenüber manuellem Parsing bevorzugt.

---

## nene2.use_case

### `UseCaseProtocol[I, O]`

Struktureller Vertrag für synchrone UseCases.

```python
from nene2.use_case import UseCaseProtocol

class MyUseCase:
    def execute(self, input_: MyInput) -> MyOutput: ...

assert isinstance(MyUseCase(), UseCaseProtocol)
```

### `AsyncUseCaseProtocol[I, O]`

Struktureller Vertrag für asynchrone UseCases.

```python
from nene2.use_case import AsyncUseCaseProtocol

class MyAsyncUseCase:
    async def execute(self, input_: MyInput) -> MyOutput: ...

assert isinstance(MyAsyncUseCase(), AsyncUseCaseProtocol)
```

> **Hinweis**: `isinstance` prüft nur das Vorhandensein von Attributen. Die async/sync-Unterscheidung wird statisch durch `mypy --strict` erzwungen.

---

## nene2.config

### `AppSettings`

Pydantic-Settings-Klasse — liest aus Umgebungsvariablen und `.env`.

```python
from nene2.config import AppSettings

cfg = AppSettings()                                   # aus der Umgebung
cfg_test = AppSettings(throttle_enabled=False)        # Überschreibung für Tests
```

Alle Felder finden Sie in der [Konfigurationsreferenz](configuration.md).

---

## nene2.middleware

### `ErrorHandlerMiddleware`

Fängt alle unbehandelten Ausnahmen ab und wandelt sie in Problem-Details-Antworten um. Registrieren Sie Domain-Ausnahme-Handler über `DomainExceptionHandlerProtocol`.

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

# Registrierung — als domain_handlers-Liste übergeben:
app.add_middleware(
    ErrorHandlerMiddleware,
    debug=settings.app_debug,
    domain_handlers=[NoteNotFoundExceptionHandler()],
)
```

`DomainExceptionHandlerProtocol` erfordert zwei Methoden:

| Methode | Signatur | Zweck |
|---|---|---|
| `handles` | `(exc: Exception) -> bool` | `True` zurückgeben, wenn dieser Handler die Ausnahme besitzt |
| `handle` | `(exc: Exception) -> Response` | Ausnahme in eine HTTP-Antwort umwandeln |

### Andere Middleware

| Klasse | Modul | Rolle |
|---|---|---|
| `SecurityHeadersMiddleware` | `nene2.middleware.security_headers` | Sicherheits-Response-Header hinzufügen |
| `RequestIdMiddleware` | `nene2.middleware.request_id` | `X-Request-ID` generieren / weitergeben |
| `RequestLoggingMiddleware` | `nene2.middleware.request_logging` | Strukturiertes Anfrage-/Antwort-Logging |
| `RequestSizeLimitMiddleware` | `nene2.middleware.request_size_limit` | Zu große Request-Bodies ablehnen |
| `ThrottleMiddleware` | `nene2.middleware.throttle` | Festfenster-Rate-Limiting pro IP |

#### `add_middleware`-Argumente

Starlette wendet Middleware in **umgekehrter Registrierungsreihenfolge** an — die zuletzt registrierte wird zur äußersten Schicht. Registrieren Sie `ErrorHandlerMiddleware` zuerst, damit sie alle Ausnahmen von jeder anderen Middleware abfängt.

| Middleware | Keyword-Argumente | Standard |
|---|---|---|
| `ErrorHandlerMiddleware` | `debug: bool`, `domain_handlers: list[DomainExceptionHandlerProtocol] \| None` | `False`, `None` |
| `SecurityHeadersMiddleware` | *(keine)* | — |
| `RequestIdMiddleware` | *(keine)* | — |
| `RequestLoggingMiddleware` | *(keine)* | — |
| `RequestSizeLimitMiddleware` | `max_bytes: int` | `1_048_576` (1 MiB) |
| `ThrottleMiddleware` | `limit: int`, `window: int` | `60`, `60` |

`ThrottleMiddleware` hat kein `enabled`-Flag — verwenden Sie `if settings.throttle_enabled:` zum Deaktivieren.

> **Hinweis — `X-Forwarded-For`-Spoofing**: Der Rate-Limit-Schlüssel wird aus dem ersten Eintrag des `X-Forwarded-For`-Headers abgeleitet, den Clients fälschen können. In der Produktion platzieren Sie die Anwendung immer hinter einem vertrauenswürdigen Reverse-Proxy (nginx, Caddy, AWS ALB, usw.), der `X-Forwarded-For` umschreibt, bevor die Anfrage die App erreicht. Einzelheiten finden Sie in [ADR-0006](../adr/0006-rate-limiting.md).

#### Vollständige Registrierungsreihenfolge mit optionaler Middleware

```python
# Registrierungsreihenfolge: innerste zuerst, äußerste zuletzt.
# Starlette führt in umgekehrter Reihenfolge aus — die zuletzt registrierte umschließt alle anderen.
app.add_middleware(ErrorHandlerMiddleware, debug=settings.app_debug, domain_handlers=[...])
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_body_size)
if settings.throttle_enabled:
    app.add_middleware(ThrottleMiddleware, limit=settings.throttle_limit, window=settings.throttle_window)
# Auth-Middleware — vor CORS registriert, damit sie innerhalb der CORS-Schicht sitzt
if settings.bearer_token_enabled:
    app.add_middleware(BearerTokenMiddleware, verifier=LocalTokenVerifier(settings.bearer_tokens))
if settings.api_key_enabled:
    app.add_middleware(ApiKeyAuthMiddleware, verifier=LocalTokenVerifier(settings.api_keys))
# CORS muss die äußerste Schicht sein — zuletzt registrieren.
# OPTIONS-Preflight-Anfragen müssen CORSMiddleware vor jeder Auth-Prüfung erreichen.
# Wenn CORSMiddleware vor Auth-Middleware registriert wird, wird die Auth-Schicht
# äußerste und gibt 401 bei Preflight zurück, was CORS für alle Browser bricht.
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
```

> **CORS + Auth-Regel**: Registrieren Sie `CORSMiddleware` immer *nach* Auth-Middleware. In Starletttes umgekehrter Reihenfolge bedeutet "zuletzt registriert = äußerste", dass CORS Auth umschließt, sodass Browser-Preflight-Anfragen (`OPTIONS`) vor der Authentifizierung behandelt werden.

### `setup_middlewares()`

Registriert den vollständigen nene2-Middleware-Stack in der korrekten LIFO-Reihenfolge (einschließlich optionalem CORS). Bevorzugen Sie dies gegenüber manuellen `add_middleware`-Aufrufen, wenn Sie keine benutzerdefinierte Middleware benötigen.

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

Siehe [middleware-stack How-to](../how-to/middleware-stack.md).

### `SimpleDomainHandler`

Helfer zum Aufbauen von `DomainExceptionHandlerProtocol` aus einem Ausnahmetyp und Statuscode.

### Rate-Limit-Speicher

| Symbol | Rolle |
|---|---|
| `RateLimitStorageProtocol` | Austauschbarer Speicher für Throttle-Zähler |
| `InMemoryRateLimitStorage` | Standard-In-Process-Implementierung |
| `ThrottleMiddleware` | Akzeptiert optionales `storage=` für benutzerdefinierte Backends |

---

## nene2.auth

### `LocalTokenVerifier`

Verifiziert Tokens gegen eine statische Liste mit `secrets.compare_digest`.

```python
from nene2.auth import LocalTokenVerifier

verifier = LocalTokenVerifier(["token-a", "token-b"])
verifier.verify("token-a")  # True
verifier.verify("wrong")    # False
```

### `TokenVerifierProtocol` / `TokenIssuerProtocol`

Strukturelle Verträge für benutzerdefinierte Verifizierer und Aussteller (z. B. JWT).

### `TokenVerificationException`

Lösen Sie dies aus einem Verifizierer aus, um einen ungültigen Token zu signalisieren. `BearerTokenMiddleware` ordnet es `401 Unauthorized` zu.

### `CompositeAuthMiddleware`

Pfad-Präfix-Regeln für gemischte Auth (z. B. Bearer auf `/api/*`, API-Key auf `/internal/*`).

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

Entwicklungshelfer für HMAC-signierte Bearer-Tokens (siehe geschützte Routen in `src/example/`).

### `make_require_auth()`

FastAPI-`Depends()`-Factory, die 401 Problem Details zurückgibt, wenn Auth-Header fehlen.

---

## nene2.database

### `SqlAlchemyQueryExecutor`

Führt parametrisiertes SQL über SQLAlchemy Core aus.

```python
from nene2.database import SqlAlchemyQueryExecutor

executor = SqlAlchemyQueryExecutor(engine)
rows = executor.fetch_all("SELECT * FROM notes WHERE id = :id", {"id": 1})
executor.write("INSERT INTO notes (title, body) VALUES (:t, :b)", {"t": "t", "b": "b"})
```

#### Rückgabewert von `write()`

`write()` gibt ein `int` zurück, dessen Bedeutung von der SQL-Operation abhängt:

| Operation | Rückgabewert |
|---|---|
| `INSERT` mit `AUTOINCREMENT` / `SERIAL` | `lastrowid` — der Primärschlüssel der neuen Zeile (immer > 0) |
| `INSERT` ohne Auto-PK oder Multi-Row-`INSERT` | `rowcount` — Anzahl der eingefügten Zeilen |
| `UPDATE` / `DELETE` | `rowcount` — betroffene Zeilen (0 wenn nichts zutraf) |

### `SqlAlchemyTransactionManager`

Verwaltet Transaktionen. Bevorzugen Sie `transactional()` gegenüber manuellen `begin/commit/rollback`-Aufrufen.

```python
from nene2.database import SqlAlchemyTransactionManager

mgr = SqlAlchemyTransactionManager(engine)

result = mgr.transactional(
    lambda ex: ex.fetch_one("SELECT COUNT(*) AS cnt FROM notes")
)
```

`transactional()` verwendet intern `engine.begin()` — jede Ausnahme innerhalb des Callbacks löst einen automatischen Rollback aus.

### `DatabaseHealthCheck`

Implementiert `HealthCheckProtocol` — verifiziert die Datenbankverbindung und gibt einen `HealthStatus` zurück.

```python
from nene2.database import DatabaseHealthCheck
from nene2.http import HealthStatus

health = DatabaseHealthCheck(engine)
status: HealthStatus = health.check()
# status.status → "ok" or "error"
# status.checks → {"db": "ok"} or {"db": "error: <message>"}
```

### `DatabaseConnectionException`

Wird von `DatabaseHealthCheck` oder Repository-Operationen ausgelöst, wenn die Datenbank nicht erreichbar ist.

---

## nene2.mcp

### `LocalMcpServer`

Umschließt FastMCP — registriert UseCase-Funktionen als MCP-Tools.

```python
from nene2.mcp import LocalMcpServer

server = LocalMcpServer("my-server", instructions="...")

@server.tool("List all notes.")
def list_notes(limit: int = 20, offset: int = 0) -> list[dict]: ...

server.run(transport="stdio")
```

### `HttpxMcpClient`

HTTP-Client zum Aufrufen einer nene2-API aus MCP-Tool-Handlern.

```python
from nene2.mcp import HttpxMcpClient

client = HttpxMcpClient("bearer-token")
response = client.get("http://localhost:8080", "/notes")
response.is_successful()   # True
response.body              # str — roher Antworttext
response.status_code       # int
response.request_id()      # str | None — Wert des X-Request-ID-Headers
```

### `McpHttpResponse`

Rückgabetyp von `HttpxMcpClient`-Methoden.

Felder: `status_code: int`, `headers: dict[str, str]`, `body: str` (roher Antworttext).

Methoden:
- `is_successful() -> bool` — `True` wenn `200 ≤ status_code < 300`
- `request_id() -> str | None` — gibt den `X-Request-ID`-Antwort-Header-Wert zurück, oder `None`

### `McpHttpClientProtocol`

Struktureller Vertrag für benutzerdefinierte MCP-HTTP-Clients. Implementieren Sie `get()`, `post()`, `put()`, `delete()` mit Rückgabe von `McpHttpResponse` und `has_authentication() -> bool`.

---

## nene2.log

### `setup_logging()`

Initialisiert structlog. Wechselt zwischen ConsoleRenderer (lokal) und JSON (Produktion).

```python
from nene2.log import setup_logging

setup_logging(app_env="production")  # JSON-Renderer
setup_logging(app_env="local")       # Konsolen-Renderer
```

---

## nene2.validation

### `ValidationException` / `ValidationError`

Lösen Sie `ValidationException` an der HTTP-Grenze aus, um `422 Unprocessable Entity` zurückzugeben.

```python
from nene2.validation.exceptions import ValidationError, ValidationException

errors = [ValidationError("body", "Body must not be empty.", "required")]
raise ValidationException(errors)
```

---

## nene2.cache

### `TtlCache[V]`

Thread-sicherer In-Memory-Cache mit TTL-Ablauf pro Schlüssel. Verwenden Sie ihn für Idempotenz-Schlüssel, kurzlebige Lookups oder Rate-Limit-Ergänzungen.

```python
from nene2.cache import TtlCache

cache: TtlCache[str] = TtlCache(ttl_seconds=60.0)
cache.set("key", "value")
cache.get("key")  # str | None
```

Siehe [lifespan-and-app-state How-to](../how-to/lifespan-and-app-state.md) für die `app.state`-Verdrahtung.

---

## nene2.security

### `verify_hmac_signature()`

Zeitkonstante HMAC-Verifizierung für Webhook-Endpunkte.

```python
from nene2.security import verify_hmac_signature

if not verify_hmac_signature(body, signature_header, secret.get_secret_value()):
    return problem_details_response("unauthorized", "Unauthorized", 401, "Invalid signature.")
```

Siehe [webhook How-to](../how-to/webhook.md).
