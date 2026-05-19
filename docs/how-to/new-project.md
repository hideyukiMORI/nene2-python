# Start a new project with nene2

This guide walks you through creating a new project that uses nene2 as a dependency — not a clone of this repository.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) installed

## 1. Initialize your project

```bash
mkdir my-api && cd my-api
uv init --name my-api --no-workspace
```

## 2. Add nene2 as a dependency

Install from GitHub (stable, latest release):

```bash
uv add "nene2-python @ git+https://github.com/hideyukiMORI/nene2-python.git"
```

## 3. Project layout

Organize your source under `src/`:

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
      sqlalchemy_repository.py   # optional — skip for InMemory only
    app.py                       # FastAPI application factory
  .env
  pyproject.toml
```

## 4. Create a domain

Follow the [Implement a new domain](../tutorials/first-domain.md) tutorial.
Use `InMemoryXxxRepository` during development — wire in `SqlAlchemyXxxRepository` when you need persistence.

## 5. Wire up the application

Create `src/app.py`:

```python
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

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

    # Middleware is applied in reverse order of registration.
    # Add the innermost (error handler) first, outermost (throttle) last.
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

    # Convert Pydantic BaseModel validation errors to RFC 9457 Problem Details
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)  # type: ignore[arg-type]

    return app


app = create_app()
```

> **Middleware ordering note:** Starlette's `add_middleware` applies middleware in reverse registration order — the last registered becomes the outermost layer. Register `ErrorHandlerMiddleware` first so it wraps everything and catches all unhandled exceptions.

## 6. Run the development server

```bash
PYTHONPATH=src uv run uvicorn app:app --reload --port 8080
```

Open `http://localhost:8080/docs` for Swagger UI.

## 7. Run tests

```bash
PYTHONPATH=src uv run pytest
```

Use `AppSettings(throttle_enabled=False)` in test fixtures to disable rate limiting:

```python
from fastapi.testclient import TestClient
from nene2.config import AppSettings
from app import create_app

client = TestClient(create_app(AppSettings(throttle_enabled=False)))
```
