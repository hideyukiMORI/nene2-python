# Design philosophy

## NENE2 core principles

nene2-python shares the same design philosophy as PHP NENE2.

### API First

The JSON API contract and OpenAPI schema are defined before the database schema. Use `uv run python src/scripts/export_openapi.py` to export a static `openapi.yaml` at any time.

### Thin HTTP layer

HTTP Handlers own no business logic. The rule is: **parse → use-case → response** — three steps, nothing more. Domain rules live in UseCases.

### AI-readable

Explicit directory structure, small classes (≤ 150 lines), typed boundaries — these let an LLM navigate and modify the codebase with confidence.

### Security first

Security is a design constraint, not an afterthought:
- All HTTP inputs validated by Pydantic at the boundary
- Parameterised queries only (SQL injection prevention)
- `secrets.compare_digest` for timing-safe token comparison
- Security headers applied by middleware on every response

### LLM Delivery Ready

Because UseCases are independent of HTTP and database, they can be registered directly as MCP tools. `src/example/mcp.py` proves this — 15 tools, zero extra plumbing.

---

## Python vs PHP NENE2

| PHP | Python | Notes |
|---|---|---|
| `readonly class` | `@dataclass(frozen=True, slots=True)` | Immutable value object |
| `ValidationException` + `ValidationError` | Same names (`nene2.validation`) | 422 + Problem Details |
| `PaginationQueryParser` | `nene2.http.PaginationQueryParser` | Query param parsing |
| `PaginationResponse` | `nene2.http.PaginationResponse` | Paginated response |
| `ProblemDetailsResponseFactory` | `nene2.http.problem_details_response()` | RFC 9457 |
| `ErrorHandlerMiddleware` | `nene2.middleware.ErrorHandlerMiddleware` | Catches all exceptions |
| `PHPStan level 8` | `mypy --strict` | Maximum type safety |
| `PHP-CS-Fixer` | `ruff format` | Code formatting |
| `UseCaseInterface` | `nene2.use_case.UseCaseProtocol[I, O]` | Structural typing |

## Python-only features

| Feature | Why Python wins |
|---|---|
| `AsyncUseCaseProtocol[I, O]` | No PHP equivalent — native coroutine protocol |
| OpenAPI auto-generation | FastAPI generates Swagger UI / ReDoc with zero config |
| Native async/await | FastAPI + uvicorn — non-blocking I/O throughout |
| MCP SDK | Anthropic's Python SDK is the reference implementation |
| `mypy --strict` | Tighter than PHPStan level 8 in practice |

## ADR index

Individual design decisions are recorded in Architecture Decision Records:

- [ADR-0001: Toolchain](../adr/0001-toolchain)
- [ADR-0002: Clean Architecture](../adr/0002-clean-architecture)
- [ADR-0003: Security First](../adr/0003-security-first)
- [ADR-0004: AI-First Design](../adr/0004-ai-first-design)
- [ADR-0005: Logging](../adr/0005-logging)
- [ADR-0006: Rate Limiting](../adr/0006-rate-limiting)
- [ADR-0009: MCP Design](../adr/0009-mcp-design)
- [ADR-0010: AsyncUseCase Pattern](../adr/0010-async-use-case)
