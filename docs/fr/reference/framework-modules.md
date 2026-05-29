# Référence des modules du framework

API publique du package `nene2`.

---

## nene2.http

### `PaginationQueryParser`

Analyse les paramètres de requête `limit` et `offset`.

**FastAPI Depends (recommandé)** :

```python
from typing import Annotated
from fastapi import Depends
from nene2.http import PaginationQueryParser

@router.get("/items")
def list_items(pagination: Annotated[PaginationQueryParser, Depends()]) -> JSONResponse:
    result = use_case.execute(pagination.limit, pagination.offset)
```

**Héritage (basé sur Request)** :

```python
from nene2.http import PaginationQueryParser

pagination = PaginationQueryParser.parse(request)
# pagination.limit  → int (max 100, défaut 20)
# pagination.offset → int (défaut 0)
```

### `PaginationResponse`

Encapsule un ensemble de résultats paginés.

```python
from nene2.http import PaginationResponse

body = PaginationResponse(items=[...], limit=20, offset=0, total=42).to_dict()
# → {"items": [...], "limit": 20, "offset": 0, "total": 42}
```

### `problem_details_response()`

Génère une réponse Problem Details RFC 9457.

```python
from nene2.http import problem_details_response

return problem_details_response("not-found", "Not Found", 404, "Note 42 not found.")
```

### `PaginationQuery`

Dataclass retourné par `PaginationQueryParser.parse()`. Contient `limit: int` et `offset: int`.

### `HealthCheckProtocol` / `HealthStatus`

Contrat et type de résultat pour les health checks de l'application.

```python
from nene2.http import HealthCheckProtocol, HealthStatus

class MyHealthCheck:
    def check(self) -> HealthStatus:
        return HealthStatus(status="ok")
```

Champs de `HealthStatus` : `status: str` (`"ok"` ou `"error"`), `checks: dict[str, str]`.
La propriété `is_healthy` retourne `True` quand `status == "ok"`.

### ETag et requêtes conditionnelles

```python
from nene2.http import check_not_modified, check_precondition, generate_etag

etag = generate_etag({"id": 1, "title": "Hello"})
# Retourne 304 quand If-None-Match correspond (GET)
check_not_modified(request, etag)
# Retourne 412 quand If-Match ne correspond pas (PUT/PATCH/DELETE)
check_precondition(request, etag)
```

### Helpers de paramètres de requête

Analyseurs typés pour les schémas de requête courants (lèvent `ValidationException` sur entrée invalide) :

```python
from nene2.http import query_array, query_bool, query_comma_separated, query_int, query_string

limit = query_int(request, "limit", default=20, minimum=1, maximum=100)
tags = query_comma_separated(request, "tags", max_items=10)
```

### `RequestScopedContext[T]`

Conteneur de valeurs à portée de requête pour l'injection de dépendances (voir [lifespan-and-app-state](../how-to/lifespan-and-app-state.md)).

### `PaginationDep`

Alias `Depends()` FastAPI pour `PaginationQueryParser` — préféré à l'analyse manuelle.

---

## nene2.use_case

### `UseCaseProtocol[I, O]`

Contrat structurel pour les UseCases synchrones.

```python
from nene2.use_case import UseCaseProtocol

class MyUseCase:
    def execute(self, input_: MyInput) -> MyOutput: ...

assert isinstance(MyUseCase(), UseCaseProtocol)
```

### `AsyncUseCaseProtocol[I, O]`

Contrat structurel pour les UseCases async.

```python
from nene2.use_case import AsyncUseCaseProtocol

class MyAsyncUseCase:
    async def execute(self, input_: MyInput) -> MyOutput: ...

assert isinstance(MyAsyncUseCase(), AsyncUseCaseProtocol)
```

> **Note** : les vérifications `isinstance` vérifient uniquement la présence de l'attribut.
> La distinction async/sync est appliquée statiquement par `mypy --strict`.

---

## nene2.config

### `AppSettings`

Classe Pydantic Settings — lit depuis les variables d'environnement et `.env`.

```python
from nene2.config import AppSettings

cfg = AppSettings()                                   # depuis l'environnement
cfg_test = AppSettings(throttle_enabled=False)        # surcharge pour les tests
```

Voir la [référence de configuration](configuration.md) pour tous les champs.

---

## nene2.middleware

### `ErrorHandlerMiddleware`

Capture toutes les exceptions non gérées et les convertit en réponses Problem Details.
Enregistrez les handlers d'exceptions de domaine via `DomainExceptionHandlerProtocol`.

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

# Enregistrement — passer comme liste domain_handlers :
app.add_middleware(
    ErrorHandlerMiddleware,
    debug=settings.app_debug,
    domain_handlers=[NoteNotFoundExceptionHandler()],
)
```

`DomainExceptionHandlerProtocol` nécessite deux méthodes :

| Méthode | Signature | Objectif |
|---|---|---|
| `handles` | `(exc: Exception) -> bool` | Retourner `True` si ce handler possède l'exception |
| `handle` | `(exc: Exception) -> Response` | Convertir l'exception en réponse HTTP |

### Autres middleware

| Classe | Module | Rôle |
|---|---|---|
| `SecurityHeadersMiddleware` | `nene2.middleware.security_headers` | Ajouter les en-têtes de sécurité dans les réponses |
| `RequestIdMiddleware` | `nene2.middleware.request_id` | Générer / propager `X-Request-ID` |
| `RequestLoggingMiddleware` | `nene2.middleware.request_logging` | Journalisation structurée des requêtes / réponses |
| `RequestSizeLimitMiddleware` | `nene2.middleware.request_size_limit` | Rejeter les corps de requête trop volumineux |
| `ThrottleMiddleware` | `nene2.middleware.throttle` | Limitation de débit par fenêtre fixe par IP |

#### Arguments `add_middleware`

Starlette applique le middleware dans l'**ordre inverse d'enregistrement** — le dernier enregistré
devient la couche la plus externe. Enregistrez `ErrorHandlerMiddleware` en premier pour qu'il
capture toutes les exceptions de chaque autre middleware.

| Middleware | Arguments nommés | Défaut |
|---|---|---|
| `ErrorHandlerMiddleware` | `debug: bool`, `domain_handlers: list[DomainExceptionHandlerProtocol] \| None` | `False`, `None` |
| `SecurityHeadersMiddleware` | *(aucun)* | — |
| `RequestIdMiddleware` | *(aucun)* | — |
| `RequestLoggingMiddleware` | *(aucun)* | — |
| `RequestSizeLimitMiddleware` | `max_bytes: int` | `1_048_576` (1 Mio) |
| `ThrottleMiddleware` | `limit: int`, `window: int` | `60`, `60` |

`ThrottleMiddleware` n'a pas de flag `enabled` — encapsulez avec `if settings.throttle_enabled:` pour le désactiver.

> **Note — spoofing de `X-Forwarded-For`** : La clé de limitation de débit est dérivée du
> premier élément de l'en-tête `X-Forwarded-For`, que les clients peuvent falsifier. En
> production, placez toujours l'application derrière un reverse proxy de confiance (nginx,
> Caddy, AWS ALB, etc.) qui réécrit `X-Forwarded-For` avant que la requête n'atteigne
> l'application. Voir [ADR-0006](../adr/0006-rate-limiting.md) pour les détails.

#### Ordre d'enregistrement complet avec middleware optionnel

```python
# Ordre d'enregistrement : le plus interne en premier, le plus externe en dernier.
# Starlette s'exécute en inverse — le dernier enregistré englobe tous les autres.
app.add_middleware(ErrorHandlerMiddleware, debug=settings.app_debug, domain_handlers=[...])
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_body_size)
if settings.throttle_enabled:
    app.add_middleware(ThrottleMiddleware, limit=settings.throttle_limit, window=settings.throttle_window)
# Middleware d'auth — enregistré avant CORS pour être à l'intérieur de la couche CORS
if settings.bearer_token_enabled:
    app.add_middleware(BearerTokenMiddleware, verifier=LocalTokenVerifier(settings.bearer_tokens))
if settings.api_key_enabled:
    app.add_middleware(ApiKeyAuthMiddleware, verifier=LocalTokenVerifier(settings.api_keys))
# CORS doit être la couche la plus externe — enregistrez-le en dernier.
# Les requêtes OPTIONS preflight doivent atteindre CORSMiddleware avant tout contrôle d'auth.
# Si CORSMiddleware est enregistré avant les middlewares d'auth, la couche auth devient
# la plus externe et retourne 401 sur les preflights, cassant CORS pour tous les navigateurs.
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
```

> **Règle CORS + Auth** : Enregistrez toujours `CORSMiddleware` *après* les middlewares d'auth.
> Dans l'ordre inverse de Starlette, "dernier enregistré = le plus externe" signifie que CORS
> englobe l'auth, de sorte que les requêtes preflight de navigateur (`OPTIONS`) sont traitées
> avant l'authentification.

### `setup_middlewares()`

Enregistre la pile middleware complète de nene2 dans le bon ordre LIFO (y compris CORS optionnel).
Préférez ceci aux appels `add_middleware` manuels quand vous n'avez pas besoin de middleware personnalisé.

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

Voir le [guide how-to middleware-stack](../how-to/middleware-stack.md).

### `SimpleDomainHandler`

Helper pour construire `DomainExceptionHandlerProtocol` à partir d'un type d'exception et d'un code statut.

### Stockage de limitation de débit

| Symbole | Rôle |
|---|---|
| `RateLimitStorageProtocol` | Stockage enfichable pour les compteurs de throttle |
| `InMemoryRateLimitStorage` | Implémentation en processus par défaut |
| `ThrottleMiddleware` | Accepte un `storage=` optionnel pour les backends personnalisés |

---

## nene2.auth

### `LocalTokenVerifier`

Vérifie les tokens contre une liste statique en utilisant `secrets.compare_digest`.

```python
from nene2.auth import LocalTokenVerifier

verifier = LocalTokenVerifier(["token-a", "token-b"])
verifier.verify("token-a")  # True
verifier.verify("wrong")    # False
```

### `TokenVerifierProtocol` / `TokenIssuerProtocol`

Contrats structurels pour les vérificateurs et émetteurs personnalisés (p. ex. JWT).

### `TokenVerificationException`

Levez ceci depuis un vérificateur pour signaler un token invalide.
`BearerTokenMiddleware` le mappe vers `401 Unauthorized`.

### `CompositeAuthMiddleware`

Règles par préfixe de chemin pour l'auth mixte (p. ex. Bearer sur `/api/*`, clé API sur `/internal/*`).

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

Helpers de développement pour les tokens bearer signés HMAC (voir les routes protégées dans `src/example/`).

### `make_require_auth()`

Factory `Depends()` FastAPI qui retourne 401 Problem Details quand les en-têtes d'auth sont manquants.

---

## nene2.database

### `SqlAlchemyQueryExecutor`

Exécute du SQL paramétré via SQLAlchemy Core.

```python
from nene2.database import SqlAlchemyQueryExecutor

executor = SqlAlchemyQueryExecutor(engine)
rows = executor.fetch_all("SELECT * FROM notes WHERE id = :id", {"id": 1})
executor.write("INSERT INTO notes (title, body) VALUES (:t, :b)", {"t": "t", "b": "b"})
```

#### Valeur de retour de `write()`

`write()` retourne un `int` dont la signification dépend de l'opération SQL :

| Opération | Valeur de retour |
|---|---|
| `INSERT` avec `AUTOINCREMENT` / `SERIAL` | `lastrowid` — la clé primaire de la nouvelle ligne (toujours > 0) |
| `INSERT` sans auto-PK, ou `INSERT` multi-lignes | `rowcount` — nombre de lignes insérées |
| `UPDATE` / `DELETE` | `rowcount` — lignes affectées (0 si rien ne correspondait) |

Utilisez `lastrowid` pour reconstruire l'entité après un INSERT d'une seule ligne :

```python
new_id = executor.write("INSERT INTO notes (title) VALUES (:title)", {"title": "Hello"})
return Note(id=new_id, title="Hello")
```

Utilisez `rowcount` pour détecter une ligne manquante sur UPDATE / DELETE :

```python
affected = executor.write("UPDATE notes SET title=:title WHERE id=:id", {"title": t, "id": pk})
if affected == 0:
    raise NoteNotFoundException(pk)
```

### `SqlAlchemyTransactionManager`

Gère les transactions. Préférez `transactional()` aux appels manuels `begin/commit/rollback`.

```python
from nene2.database import SqlAlchemyTransactionManager

mgr = SqlAlchemyTransactionManager(engine)

result = mgr.transactional(
    lambda ex: ex.fetch_one("SELECT COUNT(*) AS cnt FROM notes")
)
```

#### Combiner `transactional()` avec le schéma Repository

Quand un UseCase doit effectuer plusieurs écritures atomiques, définissez des variantes `_in_tx`
sur l'interface du repository qui acceptent un `executor` explicite. Le UseCase passe l'executor
lié à la transaction depuis le callback vers chaque méthode `_in_tx`.

**Interface du repository :**

```python
from nene2.database import DatabaseQueryExecutorInterface
from abc import ABC, abstractmethod

class AccountRepositoryInterface(ABC):
    # Méthodes standard — utilise self._executor (auto-commit)
    @abstractmethod
    def find_by_id(self, account_id: int) -> Account | None: ...

    # Variantes _in_tx — appeler uniquement dans un callback transactional()
    @abstractmethod
    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None: ...

    @abstractmethod
    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta: int
    ) -> None: ...
```

**UseCase (exemple de virement atomique) :**

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

`transactional()` utilise `engine.begin()` en interne — toute exception dans le callback
déclenche un rollback automatique.

**Tests avec InMemory :** Implémentez `DatabaseTransactionManagerInterface` avec un executor
no-op qui appelle le callback directement. Les méthodes `_in_tx` sur le repository InMemory
ignorent l'executor et opèrent sur leur store en mémoire.

### `DatabaseHealthCheck`

Implémente `HealthCheckProtocol` — vérifie la connexion à la base de données et retourne un `HealthStatus`.

```python
from nene2.database import DatabaseHealthCheck
from nene2.http import HealthStatus

health = DatabaseHealthCheck(engine)
status: HealthStatus = health.check()
# status.status → "ok" ou "error"
# status.checks → {"db": "ok"} ou {"db": "error: <message>"}
```

### `DatabaseConnectionException`

Levée par `DatabaseHealthCheck` ou les opérations du repository quand la base de données est inaccessible.

---

## nene2.mcp

### `LocalMcpServer`

Encapsule FastMCP — enregistre des fonctions UseCase comme outils MCP.

```python
from nene2.mcp import LocalMcpServer

server = LocalMcpServer("my-server", instructions="...")

@server.tool("List all notes.")
def list_notes(limit: int = 20, offset: int = 0) -> list[dict]: ...

server.run(transport="stdio")
```

### `HttpxMcpClient`

Client HTTP pour appeler une API nene2 depuis des handlers d'outils MCP.

```python
from nene2.mcp import HttpxMcpClient

client = HttpxMcpClient("bearer-token")
response = client.get("http://localhost:8080", "/notes")
response.is_successful()   # True
response.body              # str — texte de réponse brut
response.status_code       # int
response.request_id()      # str | None — valeur de l'en-tête X-Request-ID
```

### `McpHttpResponse`

Type de retour des méthodes `HttpxMcpClient`.

Champs : `status_code: int`, `headers: dict[str, str]`, `body: str` (texte de réponse brut).

Méthodes :
- `is_successful() -> bool` — `True` quand `200 ≤ status_code < 300`
- `request_id() -> str | None` — retourne la valeur de l'en-tête `X-Request-ID`, ou `None`

### `McpHttpClientProtocol`

Contrat structurel pour les clients HTTP MCP personnalisés. Implémentez `get()`, `post()`,
`put()`, `delete()` retournant `McpHttpResponse`, et `has_authentication() -> bool`.

---

## nene2.log

### `setup_logging()`

Initialise structlog. Bascule entre ConsoleRenderer (local) et JSON (production).

```python
from nene2.log import setup_logging

setup_logging(app_env="production")  # rendu JSON
setup_logging(app_env="local")       # rendu Console
```

---

## nene2.validation

### `ValidationException` / `ValidationError`

Levez `ValidationException` à la frontière HTTP pour retourner `422 Unprocessable Entity`.

```python
from nene2.validation.exceptions import ValidationError, ValidationException

errors = [ValidationError("body", "Body must not be empty.", "required")]
raise ValidationException(errors)
```

---

## nene2.cache

### `TtlCache[V]`

Cache en mémoire thread-safe avec expiration TTL par clé. Utilisez pour les clés d'idempotence,
les lookups à courte durée de vie, ou les auxiliaires de limitation de débit.

```python
from nene2.cache import TtlCache

cache: TtlCache[str] = TtlCache(ttl_seconds=60.0)
cache.set("key", "value")
cache.get("key")  # str | None
```

Voir le [guide how-to lifespan-and-app-state](../how-to/lifespan-and-app-state.md) pour le câblage `app.state`.

---

## nene2.security

### `verify_hmac_signature()`

Vérification HMAC protégée contre les attaques temporelles pour les endpoints webhook.

```python
from nene2.security import verify_hmac_signature

if not verify_hmac_signature(body, signature_header, secret.get_secret_value()):
    return problem_details_response("unauthorized", "Unauthorized", 401, "Invalid signature.")
```

Voir le [guide how-to webhook](../how-to/webhook.md).
