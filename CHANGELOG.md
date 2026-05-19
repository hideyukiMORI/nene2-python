# Changelog

All notable changes to nene2-python are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
