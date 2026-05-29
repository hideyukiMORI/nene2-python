# nene2-python

A Python reference framework implementing the [NENE2](https://github.com/hideyukiMORI/NENE2) design philosophy — clean architecture, security-first, and AI-readable code.

[![CI](https://github.com/hideyukiMORI/nene2-python/actions/workflows/ci.yml/badge.svg)](https://github.com/hideyukiMORI/nene2-python/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Current release**: `v1.8.97` · **466 tests** · CI on Python 3.12 and 3.14

---

## Features

- **FastAPI + Pydantic v2** — modern Python API stack with automatic OpenAPI docs
- **Clean Architecture** — UseCase / Domain layer fully decoupled from HTTP and DB
- **`mypy --strict`** — equivalent to PHPStan level 8 type safety
- **ruff** — lint and format in one tool (replaces flake8, isort, black, bandit)
- **RFC 9457 Problem Details** — uniform error responses across all endpoints
- **Bearer Token / API Key auth** — `LocalTokenVerifier`, `CompositeAuthMiddleware`, dev JWT helpers
- **MCP support** — expose the *same* UseCases as AI agent tools via `LocalMcpServer` ([one UseCase, two surfaces](docs/explanation/one-usecase-two-surfaces.md))
- **SQLAlchemy Core** — parameterised SQL without ORM overhead
- **Security middleware** — CSP, rate limiting, request size limit, CORS via `setup_middlewares()`
- **ETag / conditional requests** — `generate_etag()`, `check_not_modified()`, `check_precondition()`
- **TTL cache & webhooks** — `TtlCache[V]`, `verify_hmac_signature()`
- **structlog** — structured JSON logging with request ID correlation
- **219 field trials** — stdlib and framework patterns validated in sandbox apps ([INDEX](docs/field-trials/INDEX.md))

---

## Installation

```bash
pip install nene2-python
# or
uv add nene2-python
```

Requires Python 3.12+ (CI also tests 3.14).

---

## Quick Start

Use `APIRouter` + `create_app()` at the **end of the file** (see [CLAUDE.md](CLAUDE.md)). Register middlewares with `setup_middlewares()` so 500 responses still get `X-Request-Id` and security headers.

```python
from fastapi import APIRouter, FastAPI
from nene2.config import AppSettings
from nene2.middleware import setup_middlewares

router = APIRouter()

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

def create_app() -> FastAPI:
    cfg = AppSettings()
    app = FastAPI(title=cfg.app_name)
    setup_middlewares(
        app,
        debug=cfg.app_debug,
        throttle_limit=cfg.throttle_limit if cfg.throttle_enabled else None,
        cors_allowed_origins=cfg.cors_origins if cfg.cors_enabled else None,
    )
    app.include_router(router)
    return app

app = create_app()
```

See the full reference app in [`src/example/`](src/example/) (Note / Tag / Comment CRUD, auth, MCP).

---

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

router = APIRouter(prefix="/notes", tags=["notes"])

@router.get("/{note_id}")
async def get_note(note_id: int) -> JSONResponse:
    note = get_use_case.execute(GetNoteInput(note_id))
    return JSONResponse({"id": note.id, "title": note.title, "body": note.body})
```

---

## Development Commands

```bash
uv sync                         # install dependencies
uv run pytest                   # 466 tests, coverage ≥ 80%
uv run mypy src/                # type check (strict)
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
uv run pip-audit --ignore-vuln PYSEC-2025-183
```

CI also runs a **90% coverage gate** on `example/*/use_case.py`, `entity.py`, and `async_use_case.py`.

---

## Framework Modules

| Module | Purpose |
|---|---|
| `nene2.http` | Pagination, Problem Details, health checks, ETag, query helpers, `RequestScopedContext` |
| `nene2.middleware` | Full pipeline + `setup_middlewares()`, rate-limit storage protocol |
| `nene2.auth` | Bearer / API Key / composite auth, `LocalTokenIssuer`, `make_require_auth()` |
| `nene2.database` | `SqlAlchemyQueryExecutor`, `SqlAlchemyTransactionManager`, `DatabaseHealthCheck` |
| `nene2.config` | `AppSettings` (pydantic-settings, reads from env / `.env`) |
| `nene2.validation` | `ValidationException`, `ValidationError` |
| `nene2.cache` | `TtlCache[V]` — thread-safe in-memory TTL cache |
| `nene2.security` | `verify_hmac_signature()` for webhook verification |
| `nene2.mcp` | `LocalMcpServer`, `HttpxMcpClient` |
| `nene2.log` | `setup_logging()` (structlog, JSON in production) |
| `nene2.use_case` | `UseCaseProtocol[I, O]`, `AsyncUseCaseProtocol[I, O]` |

Details: [Framework modules reference](docs/reference/framework-modules.md) · [How-to guides](docs/how-to/)

---

## Versioning

- **`pyproject.toml` `version`** — bumped with each merged FT or feature PR (currently `1.8.97`).
- **Git tags** (`v1.8.N`) — created on selected releases; may lag behind `pyproject.toml` during rapid FT loops.
- See [docs/todo/current.md](docs/todo/current.md) for the latest milestone table.

---

## PHP NENE2 Correspondence

| PHP | Python |
|---|---|
| `readonly class` | `dataclass(frozen=True, slots=True)` |
| `PHPStan level 8` | `mypy --strict` |
| `PHP-CS-Fixer` | `ruff format` |
| `composer check` | `uv run pytest && mypy && ruff check && ruff format --check && pip-audit --ignore-vuln PYSEC-2025-183` |
| `ValidationException` | `nene2.validation.ValidationException` |
| `PaginationQueryParser` | `nene2.http.PaginationQueryParser` |
| `ErrorHandlerMiddleware` | `nene2.middleware.ErrorHandlerMiddleware` |
| `LocalMcpServer` | `nene2.mcp.LocalMcpServer` |

---

## Related

- [NENE2 (PHP)](https://github.com/hideyukiMORI/NENE2) — PHP reference implementation
- [Documentation (GitHub Pages)](https://hideyukimori.github.io/nene2-python/) — tutorials, how-to, reference (Diátaxis)
- [Field Trial INDEX](docs/field-trials/INDEX.md) — FT1–FT219 searchable index
- [Roadmap](docs/roadmap.md) — current status and planned work
