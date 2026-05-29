# 設計思想と PHP NENE2 との対応

## NENE2 の設計原則

nene2-python は PHP 版 NENE2 と同一の設計思想を持ちます。

### API First

JSON API と OpenAPI 契約を中心に据えます。DB 設計より先に API の形を定義し、スキーマを `uv run python src/scripts/export_openapi.py` で生成します。

### 薄い HTTP 層

HTTP Handler はビジネスロジックを持ちません。**parse → use-case → response** の 3 ステップのみ。ドメインルールは UseCase に集約されます。

### AI-readable

明示的なディレクトリ構造、小さなクラス（150 行以下）、型付き境界により、LLM がコードベースを正確に理解・操作できます。

### Security First

セキュリティは後付けではなく設計の出発点です。
- Pydantic による HTTP 境界の全入力検証
- パラメータ化クエリのみ（SQLインジェクション防止）
- `secrets.compare_digest` によるタイミング安全な比較
- セキュリティヘッダーをミドルウェアで付与

### LLM Delivery Ready

UseCase は HTTP・DB から独立しているため、MCP ツールとして直接再利用できます。`src/example/mcp.py` はその実証です。並べて見るコードと、それを守るパリティテストは [1 つの UseCase、2 つのサーフェス（HTTP + MCP）](one-usecase-two-surfaces.md) を参照してください。

## PHP NENE2 との対応表

| PHP 版 | Python 版 | 備考 |
|---|---|---|
| `readonly class` | `@dataclass(frozen=True, slots=True)` | 不変 Value Object |
| `ValidationException` + `ValidationError` | 同名クラス (`nene2.validation`) | 422 + Problem Details |
| `PaginationQueryParser` | `nene2.http.PaginationQueryParser` | クエリパラメータ解析 |
| `PaginationResponse` | `nene2.http.PaginationResponse` | ページネーションレスポンス |
| `ProblemDetailsResponseFactory` | `nene2.http.problem_details_response()` | RFC 9457 |
| `ErrorHandlerMiddleware` | `nene2.middleware.ErrorHandlerMiddleware` | 全例外をキャッチ |
| `PHPStan level 8` | `mypy --strict` | 最高レベルの型チェック |
| `PHP-CS-Fixer` | `ruff format` | コードフォーマット |
| `UseCaseInterface` | `nene2.use_case.UseCaseProtocol[I, O]` | 構造的サブタイピング |

## Python 3.12+ 固有の選択

| 用途 | 選択 | 理由 |
|---|---|---|
| 型エイリアス | `type X = list[str]` | PEP 695 — 新構文 |
| ジェネリクス | `class Foo[T]` | PEP 695 — TypeVar 不要 |
| 不変 VO | `dataclass(frozen=True, slots=True)` | メモリ効率 + 不変性 |
| HTTP 検証 | Pydantic v2 BaseModel | 高速 + 型安全 |
| SQL | SQLAlchemy Core | ORM なしで SQL を直接制御 |
| ロギング | structlog | JSON / Console の両対応 |
| MCP | mcp (Anthropic SDK) | FastMCP ラッパー |

## ADR 一覧

設計の個別決定は ADR に記録されています:

- [ADR-0001: ツールチェーン](../../adr/0001-toolchain.md)
- [ADR-0002: クリーンアーキテクチャ](../../adr/0002-clean-architecture.md)
- [ADR-0003: セキュリティファースト](../../adr/0003-security-first.md)
- [ADR-0004: AI ファースト設計](../../adr/0004-ai-first-design.md)
- [ADR-0005: ロギング](../../adr/0005-logging.md)
- [ADR-0006: レートリミット](../../adr/0006-rate-limiting.md)
- [ADR-0009: MCP 設計](../../adr/0009-mcp-design.md)
- [ADR-0010: AsyncUseCase パターン](../../adr/0010-async-use-case.md)
