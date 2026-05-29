# Démarrer un nouveau projet avec nene2

Ce guide vous explique comment créer un nouveau projet qui utilise nene2 comme dépendance —
et non un clone de ce dépôt.

## Prérequis

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) installé

## 1. Initialiser votre projet

```bash
mkdir my-api && cd my-api
uv init --name my-api --no-workspace
```

## 2. Ajouter nene2 comme dépendance

Installer depuis GitHub (stable, dernière version) :

```bash
uv add "nene2-python @ git+https://github.com/hideyukiMORI/nene2-python.git"
```

## 3. Structure du projet

Organisez vos sources sous `src/` :

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
      sqlalchemy_repository.py   # optionnel — à omettre si InMemory uniquement
    app.py                       # factory d'application FastAPI
  .env
  pyproject.toml
```

## 4. Créer un domaine

Suivez le tutoriel [Implémenter un nouveau domaine](../tutorials/first-domain.md).
Utilisez `InMemoryXxxRepository` pendant le développement — câblez `SqlAlchemyXxxRepository`
quand vous avez besoin de persistance.

## 5. Câbler l'application

Créez `src/app.py` :

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

    # Le middleware est appliqué dans l'ordre inverse d'enregistrement.
    # Ajouter le plus interne (gestionnaire d'erreurs) en premier, le plus externe (throttle) en dernier.
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
    # Middleware d'auth — enregistré avant CORS pour être à l'intérieur de la couche CORS.
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

    # Convertir les erreurs de validation Pydantic BaseModel en RFC 9457 Problem Details
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)  # type: ignore[arg-type]

    return app


app = create_app()
```

> **Note sur l'ordre des middleware :** Le `add_middleware` de Starlette applique les middleware
> dans l'ordre inverse d'enregistrement — le dernier enregistré devient la couche la plus externe.
> Enregistrez `ErrorHandlerMiddleware` en premier pour qu'il englobe tout et capture toutes les
> exceptions non gérées.

> **Règle CORS + Auth** : Enregistrez toujours `CORSMiddleware` *après* les middlewares d'auth.
> Dans l'ordre inverse de Starlette, "dernier enregistré = le plus externe" signifie que CORS
> englobe l'auth, de sorte que les requêtes preflight de navigateur (`OPTIONS`) sont traitées
> avant l'authentification.

## 6. Démarrer le serveur de développement

```bash
PYTHONPATH=src uv run uvicorn app:app --reload --port 8080
```

Ouvrez `http://localhost:8080/docs` pour Swagger UI.

## 7. Exécuter les tests

```bash
PYTHONPATH=src uv run pytest
```

Utilisez `AppSettings(throttle_enabled=False)` dans les fixtures de test pour désactiver la
limitation de débit :

```python
from fastapi.testclient import TestClient
from nene2.config import AppSettings
from app import create_app

client = TestClient(create_app(AppSettings(throttle_enabled=False)))
```
