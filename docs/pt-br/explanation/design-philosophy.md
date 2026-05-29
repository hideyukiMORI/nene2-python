# Filosofia de design

## Princípios centrais do NENE2

O nene2-python compartilha a mesma filosofia de design do PHP NENE2.

### API First

O contrato da API JSON e o schema OpenAPI são definidos antes do schema do banco de dados. Use `uv run python src/scripts/export_openapi.py` para exportar um `openapi.yaml` estático a qualquer momento.

### Camada HTTP fina

Os HTTP Handlers não possuem nenhuma lógica de negócio. A regra é: **parse → use-case → response** — três passos, nada mais. As regras de domínio vivem nos UseCases.

### AI-readable

Estrutura de diretórios explícita, classes pequenas (≤ 150 linhas), fronteiras tipadas — isso permite que um LLM navegue e modifique o código com confiança.

### Security first

Segurança é uma restrição de design, não um pensamento tardio:
- Todas as entradas HTTP validadas pelo Pydantic na fronteira
- Apenas queries parametrizadas (prevenção de SQL injection)
- `secrets.compare_digest` para comparação de tokens segura contra timing attacks
- Headers de segurança aplicados pelo middleware em toda resposta

### LLM Delivery Ready

Como os UseCases são independentes de HTTP e banco de dados, eles podem ser registrados diretamente como ferramentas MCP. `src/example/mcp.py` prova isso — 15 ferramentas, zero plumbing extra. Veja [Um UseCase, duas superfícies (HTTP + MCP)](one-usecase-two-surfaces.md) para o código lado a lado e o teste de paridade que o protege.

---

## Python vs PHP NENE2

| PHP | Python | Notas |
|---|---|---|
| `readonly class` | `@dataclass(frozen=True, slots=True)` | Objeto de valor imutável |
| `ValidationException` + `ValidationError` | Mesmos nomes (`nene2.validation`) | 422 + Problem Details |
| `PaginationQueryParser` | `nene2.http.PaginationQueryParser` | Parse de query params |
| `PaginationResponse` | `nene2.http.PaginationResponse` | Resposta paginada |
| `ProblemDetailsResponseFactory` | `nene2.http.problem_details_response()` | RFC 9457 |
| `ErrorHandlerMiddleware` | `nene2.middleware.ErrorHandlerMiddleware` | Captura todas as exceções |
| `PHPStan level 8` | `mypy --strict` | Máxima segurança de tipos |
| `PHP-CS-Fixer` | `ruff format` | Formatação de código |
| `UseCaseInterface` | `nene2.use_case.UseCaseProtocol[I, O]` | Tipagem estrutural |

## Funcionalidades exclusivas do Python

| Funcionalidade | Por que o Python se destaca |
|---|---|
| `AsyncUseCaseProtocol[I, O]` | Sem equivalente em PHP — protocolo de coroutine nativo |
| Geração automática de OpenAPI | FastAPI gera Swagger UI / ReDoc com zero configuração |
| async/await nativo | FastAPI + uvicorn — I/O não bloqueante por toda a aplicação |
| MCP SDK | O SDK Python da Anthropic é a implementação de referência |
| `mypy --strict` | Na prática mais rigoroso que PHPStan level 8 |

## Índice de ADRs

Decisões de design individuais estão registradas em Architecture Decision Records:

- [ADR-0001: Toolchain](../adr/0001-toolchain.md)
- [ADR-0002: Clean Architecture](../adr/0002-clean-architecture.md)
- [ADR-0003: Security First](../adr/0003-security-first.md)
- [ADR-0004: AI-First Design](../adr/0004-ai-first-design.md)
- [ADR-0005: Logging](../adr/0005-logging.md)
- [ADR-0006: Rate Limiting](../adr/0006-rate-limiting.md)
- [ADR-0009: MCP Design](../adr/0009-mcp-design.md)
- [ADR-0010: AsyncUseCase Pattern](../adr/0010-async-use-case.md)
