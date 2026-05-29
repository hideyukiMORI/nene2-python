# Ein neues Projekt mit nene2 starten

Dieser Leitfaden führt Sie durch das Erstellen eines neuen Projekts, das nene2 als Abhängigkeit verwendet — kein Klon dieses Repositories.

## Voraussetzungen

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) installiert

## 1. Projekt initialisieren

```bash
mkdir my-api && cd my-api
uv init --name my-api --no-workspace
```

## 2. nene2 als Abhängigkeit hinzufügen

Von GitHub installieren (stabil, neueste Version):

```bash
uv add "nene2-python @ git+https://github.com/hideyukiMORI/nene2-python.git"
```

## 3. Projektstruktur

Organisieren Sie Ihren Quellcode unter `src/`:

```
my-api/
  src/
    myapp/
      __init__.py
      entity.py
      repository.py
      exceptions.py
      use_case.py
      handler.py
      sqlalchemy_repository.py   # optional — für InMemory-only überspringen
    app.py                       # FastAPI-Anwendungsfactory
  .env
  pyproject.toml
```

## 4. Eine Domain erstellen

Folgen Sie dem Tutorial [Eine neue Domain implementieren](../tutorials/first-domain.md).
Verwenden Sie `InMemoryXxxRepository` während der Entwicklung — binden Sie `SqlAlchemyXxxRepository` ein, wenn Sie Persistenz benötigen.

## 5. Die Anwendung verdrahten

Erstellen Sie `src/app.py`:

```python
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from fastapi.middleware.cors import CORSMiddleware

from nene2.auth import ApiKeyAuthMiddleware, BearerTokenMiddleware, LocalTokenVerifier
from nene2.config import AppSettings
from nene2.log import setup_logging
from nene2.middleware import ErrorHandlerMiddleware
from nene2.middleware.error_handler import request_validation_error_handler
from nene2.middleware.request_id import RequestIdMiddleware
from nene2.middleware.request_logging import RequestLoggingMiddleware
from nene2.middleware.request_size_limit import RequestSizeLimitMiddleware
from nene2.middleware.security_headers import SecurityHeadersMiddleware
from nene2.middleware.throttle import ThrottleMiddleware

from myapp.exceptions import MyEntityNotFoundExceptionHandler
from myapp.handler import make_my_router
from myapp.repository import InMemoryMyRepository
from myapp.use_case import CreateMyUseCase, DeleteMyUseCase, GetMyUseCase, ListMyUseCase, UpdateMyUseCase


def create_app(settings: AppSettings | None = None) -> FastAPI:
    if settings is None:
        settings = AppSettings()

    setup_logging(app_env=settings.app_env)

    app = FastAPI(title="my-api", version="0.1.0")

    repo = InMemoryMyRepository()
    app.include_router(make_my_router(
        list_use_case=ListMyUseCase(repo),
        get_use_case=GetMyUseCase(repo),
        create_use_case=CreateMyUseCase(repo),
        update_use_case=UpdateMyUseCase(repo),
        delete_use_case=DeleteMyUseCase(repo),
    ))

    # Middleware wird in umgekehrter Registrierungsreihenfolge angewendet.
    # Innerste (Fehler-Handler) zuerst hinzufügen, äußerste (Throttle) zuletzt.
    app.add_middleware(
        ErrorHandlerMiddleware,
        debug=settings.app_debug,
        domain_handlers=[MyEntityNotFoundExceptionHandler()],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_body_size)
    if settings.throttle_enabled:
        app.add_middleware(
            ThrottleMiddleware,
            limit=settings.throttle_limit,
            window=settings.throttle_window,
        )
    # Auth-Middleware — vor CORS registriert, damit sie innerhalb der CORS-Schicht sitzt.
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

    # Pydantic BaseModel-Validierungsfehler in RFC 9457 Problem Details umwandeln
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)  # type: ignore[arg-type]

    return app


app = create_app()
```

> **Hinweis zur Middleware-Reihenfolge:** Starletttes `add_middleware` wendet Middleware in umgekehrter Registrierungsreihenfolge an — die zuletzt registrierte wird zur äußersten Schicht. Registrieren Sie `ErrorHandlerMiddleware` zuerst, damit sie alles umschließt und alle unbehandelten Ausnahmen abfängt.

> **CORS + Auth-Regel**: Registrieren Sie `CORSMiddleware` immer *nach* Auth-Middleware. In Starletttes umgekehrter Reihenfolge bedeutet "zuletzt registriert = äußerste", dass CORS Auth umschließt, sodass Browser-Preflight-Anfragen (`OPTIONS`) vor der Authentifizierung behandelt werden.

## 6. Entwicklungsserver starten

```bash
PYTHONPATH=src uv run uvicorn app:app --reload --port 8080
```

Öffnen Sie `http://localhost:8080/docs` für Swagger UI.

## 7. Tests ausführen

```bash
PYTHONPATH=src uv run pytest
```

Verwenden Sie `AppSettings(throttle_enabled=False)` in Test-Fixtures, um Rate-Limiting zu deaktivieren:

```python
from fastapi.testclient import TestClient
from nene2.config import AppSettings
from app import create_app

client = TestClient(create_app(AppSettings(throttle_enabled=False)))
```
