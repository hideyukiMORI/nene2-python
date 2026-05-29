# 设计哲学

## NENE2 核心原则

nene2-python 与 PHP NENE2 共享相同的设计哲学。

### API 优先

JSON API 契约和 OpenAPI schema 在数据库 schema 之前定义。随时可以通过 `uv run python src/scripts/export_openapi.py` 导出静态的 `openapi.yaml`。

### 薄 HTTP 层

HTTP Handler 不承载任何业务逻辑。原则是：**解析 → UseCase → 响应** — 三步，仅此而已。领域规则在 UseCase 中实现。

### AI 可读

明确的目录结构、小型类（≤ 150 行）、有类型约束的边界 — 这些设计让 LLM 能够自信地导航和修改代码库。

### 安全优先

安全是设计约束，而非事后补救：
- 所有 HTTP 输入在边界处由 Pydantic 验证
- 仅使用参数化查询（防止 SQL 注入）
- 使用 `secrets.compare_digest` 进行防时序攻击的 Token 比较
- 每个响应都由 middleware 附加安全响应头

### LLM 交付就绪

由于 UseCase 独立于 HTTP 和数据库，可以直接注册为 MCP 工具。`src/example/mcp.py` 验证了这一点 — 15 个工具，零额外配置。详情参阅 [一个 UseCase，两个接入面（HTTP + MCP）](one-usecase-two-surfaces.md) 中的并排代码对比和防回归测试。

---

## Python 版与 PHP NENE2 对比

| PHP | Python | 说明 |
|---|---|---|
| `readonly class` | `@dataclass(frozen=True, slots=True)` | 不可变值对象 |
| `ValidationException` + `ValidationError` | 同名类（`nene2.validation`） | 422 + Problem Details |
| `PaginationQueryParser` | `nene2.http.PaginationQueryParser` | 查询参数解析 |
| `PaginationResponse` | `nene2.http.PaginationResponse` | 分页响应 |
| `ProblemDetailsResponseFactory` | `nene2.http.problem_details_response()` | RFC 9457 |
| `ErrorHandlerMiddleware` | `nene2.middleware.ErrorHandlerMiddleware` | 捕获所有异常 |
| `PHPStan level 8` | `mypy --strict` | 最高类型安全级别 |
| `PHP-CS-Fixer` | `ruff format` | 代码格式化 |
| `UseCaseInterface` | `nene2.use_case.UseCaseProtocol[I, O]` | 结构化类型 |

## Python 独有特性

| 特性 | Python 的优势 |
|---|---|
| `AsyncUseCaseProtocol[I, O]` | PHP 无等价物 — 原生协程协议 |
| OpenAPI 自动生成 | FastAPI 零配置生成 Swagger UI / ReDoc |
| 原生 async/await | FastAPI + uvicorn — 全程非阻塞 I/O |
| MCP SDK | Anthropic 的 Python SDK 为参考实现 |
| `mypy --strict` | 实践中比 PHPStan level 8 更严格 |

## ADR 索引

各项设计决策记录在架构决策记录（ADR）中：

- [ADR-0001: 工具链](../adr/0001-toolchain.md)
- [ADR-0002: 整洁架构](../adr/0002-clean-architecture.md)
- [ADR-0003: 安全优先](../adr/0003-security-first.md)
- [ADR-0004: AI 优先设计](../adr/0004-ai-first-design.md)
- [ADR-0005: 日志](../adr/0005-logging.md)
- [ADR-0006: 限流](../adr/0006-rate-limiting.md)
- [ADR-0009: MCP 设计](../adr/0009-mcp-design.md)
- [ADR-0010: AsyncUseCase 模式](../adr/0010-async-use-case.md)
