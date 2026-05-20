# Changelog

All notable changes to nene2-python are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.6.0] — 2026-05-20

FT13 (ValidationException実運用) field trial — validation DX improvements.

### Added
- `ValidationException.single(field, message, code)` — convenience classmethod for single-error raises
- `ValidationError.__post_init__` now names the specific empty field in the error message
- Field trial report: `docs/field-trials/2026-05-field-trial-13.md`

---

## [1.5.0] — 2026-05-20

FT12 (ThrottleMiddleware + RequestSizeLimitMiddleware) field trial — middleware exclude_paths consistency.

### Added
- `ThrottleMiddleware` — `exclude_paths` parameter to bypass rate limiting for `/health`, `/docs`, etc.
- `RequestSizeLimitMiddleware` — same `exclude_paths` parameter for consistency with other middleware
- Field trial report: `docs/field-trials/2026-05-field-trial-12.md`

---

## [1.4.0] — 2026-05-20

FT11 (BearerTokenMiddleware + HttpxMcpClient) field trial — auth usability improvements.

### Added
- `BearerTokenMiddleware` — `exclude_paths` parameter to bypass auth for `/docs`, `/openapi.json`, `/health`, etc.
- `ApiKeyAuthMiddleware` — same `exclude_paths` parameter
- `LocalTokenVerifier.from_env(env_var, *, separator=",")` — create a verifier from a comma-delimited environment variable, with whitespace trimming and custom separator support
- `docs/how-to/configure-auth.md` — three new sections: `from_env` usage, `exclude_paths` usage, MCP server fail-fast token check pattern
- Field trial report: `docs/field-trials/2026-05-field-trial-11.md`

---

## [1.3.0] — 2026-05-20

FT10 (MySQL adapter) field trial — pagination and serialization improvements.

### Added
- `PaginationQueryParser.__init__` — makes the class usable as a FastAPI `Depends()` parameter directly: `Annotated[PaginationQueryParser, Depends()]`
- `PaginationResponse.to_dict()` — auto-serializes `dataclass(frozen=True, slots=True)` items via `dataclasses.asdict()` (previously raised `TypeError` for slotted dataclasses)
- Field trial report: `docs/field-trials/2026-05-field-trial-10.md`
- How-to guide: MySQL adapter setup (`docs/how-to/use-mysql.md`)

---

## [1.2.0] — 2026-05-19

FT9 (MCP server standalone) field trial — MCP server and HTTP client improvements.

### Added
- `LocalMcpServer` — `port` and `host` constructor parameters (previously hardcoded)
- `McpHttpError` — raised by `HttpxMcpClient.raise_for_error()` on 4xx/5xx responses, maps to MCP `isError: true`
- Field trial report: `docs/field-trials/2026-05-field-trial-9.md`

---

## [1.1.0] — 2026-05-19

FT8 (nested resources + datetime) field trial — database datetime handling.

### Added
- `nene2.database.utils.parse_db_datetime(value)` — normalises SQLite string timestamps and MySQL naive `datetime` objects to UTC-aware `datetime`; handles both adapters transparently
- Field trial report: `docs/field-trials/2026-05-field-trial-8.md`

---

## [1.0.0] — 2026-05-19

First stable release. Feature parity with PHP NENE2 v1.4.0.

### Added

**Core framework (`nene2`)**
- `nene2.use_case` — `UseCaseProtocol[I, O]` and `AsyncUseCaseProtocol[I, O]` (Python 3.12 generics + `@runtime_checkable`)
- `nene2.auth` — `TokenIssuerProtocol`, `TokenVerificationException`, `BearerTokenMiddleware`, `ApiKeyAuthMiddleware`, `LocalTokenVerifier`
- `nene2.database` — `DatabaseQueryExecutorInterface`, `DatabaseTransactionManagerInterface` with `transactional(callback)` pattern, `SqlAlchemyQueryExecutor`, `SqlAlchemyTransactionManager`, `_BoundQueryExecutor`
- `nene2.mcp` — `LocalMcpServer` (FastMCP wrapper), `McpHttpClientProtocol`, `McpHttpResponse`, `HttpxMcpClient`
- `nene2.middleware` — `ErrorHandlerMiddleware`, `SecurityHeadersMiddleware`, `RequestIdMiddleware`, `RequestLoggingMiddleware`, `RequestSizeLimitMiddleware`, `ThrottleMiddleware`
- `nene2.http` — `PaginationQueryParser`, `PaginationResponse`, `problem_details_response()` (RFC 9457)
- `nene2.log` — structlog setup (JSON for production, ConsoleRenderer for local)
- `nene2.config` — `AppSettings` with Pydantic Settings (SQLite / MySQL / PostgreSQL)
- `nene2.validation` — `ValidationException`, `ValidationError`

**Example application (`example`)**
- Note, Tag, Comment domains — full CRUD (entity / repository / use_case / handler / SQLAlchemy repository)
- `AsyncListNotesUseCase`, `AsyncGetNoteUseCase` — demonstrates `AsyncUseCaseProtocol` with `asyncio.gather`
- `create_mcp_server()` — 15 MCP tools (Note × 5, Tag × 5, Comment × 5)
- `/health` endpoint with DB health check
- `export-openapi` script — exports static `docs/openapi.yaml`

**Documentation (Diátaxis)**
- Tutorial: Getting started, Implement a new domain
- How-to: Add new domain, Configure auth, MCP setup, Run tests
- Explanation: Architecture overview, Design philosophy & PHP correspondence
- Reference: Configuration, Framework modules, REST API
- ADR-0001 through ADR-0010

**Infra**
- GitHub Actions CI (pytest + mypy + ruff + pip-audit)
- GitHub Pages (VitePress) with Python-themed dark design
- VitePress docs site with Python Yellow/Blue branding

### Architecture highlights
- Clean Architecture: HTTP Handler → UseCase → RepositoryInterface → SQLAlchemy
- `mypy --strict` on all source files
- `ruff` lint + format (S, ANN, UP, B, SIM, PL, and more)
- 165 tests, 92% coverage

---

## [0.1.0] — 2026-05-19

Initial implementation commit.
