# nene2-python

A Python reference framework implementing the [NENE2](https://github.com/hideyukiMORI/NENE2) design philosophy — clean architecture, security-first, and AI-readable code.

[![CI](https://github.com/hideyukiMORI/nene2-python/actions/workflows/ci.yml/badge.svg)](https://github.com/hideyukiMORI/nene2-python/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Features

- **FastAPI + Pydantic v2** — modern Python API stack with automatic OpenAPI docs
- **Clean Architecture** — UseCase / Domain layer fully decoupled from HTTP and DB
- **`mypy --strict`** — equivalent to PHPStan level 8 type safety
- **ruff** — lint and format in one tool (replaces flake8, isort, black, bandit)
- **RFC 9457 Problem Details** — uniform error responses across all endpoints
- **Bearer Token / API Key auth** — zero-config `LocalTokenVerifier`
- **MCP support** — expose UseCases as AI agent tools via `LocalMcpServer`
- **SQLAlchemy Core** — parameterised SQL without ORM overhead
- **Security middleware** — CSP, X-Frame-Options, rate limiting, request size limit, CORS
- **structlog** — structured JSON logging with request ID correlation

---

## Installation

```bash
pip install nene2-python
# or
uv add nene2-python
```

Requires Python 3.12+.

---

## Quick Start

```python
from fastapi import FastAPI
from nene2.config import AppSettings
from nene2.middleware import (
    ErrorHandlerMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    ThrottleMiddleware,
)

cfg = AppSettings()
app = FastAPI()

app.add_middleware(ErrorHandlerMiddleware, debug=cfg.app_debug)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(ThrottleMiddleware, limit=cfg.throttle_limit, window=cfg.throttle_window)
```

### Define a domain

```python
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass(frozen=True, slots=True)
class Note:
    id: int
    title: str
    body: str

class NoteRepositoryInterface(ABC):
    @abstractmethod
    def find_by_id(self, note_id: int) -> Note | None: ...

@dataclass(frozen=True, slots=True)
class GetNoteInput:
    note_id: int

class GetNoteUseCase:
    def __init__(self, repository: NoteRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: GetNoteInput) -> Note:
        note = self._repository.find_by_id(input_.note_id)
        if note is None:
            raise NoteNotFoundException(input_.note_id)
        return note
```

### Wire to HTTP

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from nene2.http import problem_details_response

router = APIRouter(prefix="/notes", tags=["notes"])

@router.get("/{note_id}")
async def get_note(note_id: int) -> JSONResponse:
    note = get_use_case.execute(GetNoteInput(note_id))
    return JSONResponse({"id": note.id, "title": note.title, "body": note.body})
```

See the full working example in [`src/example/`](src/example/).

---

## Development Commands

```bash
uv sync                         # install dependencies
uv run pytest                   # run tests (coverage enforced at 80%)
uv run mypy src/                # type check
uv run ruff check src/ tests/   # lint
uv run ruff format src/ tests/  # format
uv run uvicorn src.example.app:app --reload --port 8080  # dev server
```

Full CI check (equivalent to GitHub Actions):

```bash
uv run pytest && \
uv run mypy src/ && \
uv run ruff check src/ tests/ && \
uv run ruff format --check src/ tests/ && \
uv run pip-audit
```

---

## Framework Modules

| Module | Purpose |
|---|---|
| `nene2.http` | `PaginationQueryParser`, `PaginationResponse`, `problem_details_response()` |
| `nene2.middleware` | `ErrorHandlerMiddleware`, `SecurityHeadersMiddleware`, `RequestIdMiddleware`, `RequestLoggingMiddleware`, `RequestSizeLimitMiddleware`, `ThrottleMiddleware` |
| `nene2.auth` | `BearerTokenMiddleware`, `ApiKeyAuthMiddleware`, `LocalTokenVerifier`, `TokenVerifierProtocol` |
| `nene2.database` | `SqlAlchemyQueryExecutor`, `SqlAlchemyTransactionManager`, `DatabaseHealthCheck` |
| `nene2.config` | `AppSettings` (pydantic-settings, reads from env / `.env`) |
| `nene2.validation` | `ValidationException`, `ValidationError` |
| `nene2.mcp` | `LocalMcpServer`, `HttpxMcpClient` |
| `nene2.log` | `setup_logging()` (structlog, JSON in production) |
| `nene2.use_case` | `UseCaseProtocol[I, O]`, `AsyncUseCaseProtocol[I, O]` |

---

## PHP NENE2 Correspondence

| PHP | Python |
|---|---|
| `readonly class` | `dataclass(frozen=True, slots=True)` |
| `PHPStan level 8` | `mypy --strict` |
| `PHP-CS-Fixer` | `ruff format` |
| `composer check` | `uv run pytest && mypy && ruff check && ruff format --check && pip-audit` |
| `ValidationException` | `nene2.validation.ValidationException` |
| `PaginationQueryParser` | `nene2.http.PaginationQueryParser` |
| `ErrorHandlerMiddleware` | `nene2.middleware.ErrorHandlerMiddleware` |
| `LocalMcpServer` | `nene2.mcp.LocalMcpServer` |

---

## Related

- [NENE2 (PHP)](https://github.com/hideyukiMORI/NENE2) — PHP reference implementation
- [Documentation](https://hideyukimori.github.io/nene2-python/) — full docs (Diátaxis structure)
