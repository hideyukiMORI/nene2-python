# Roadmap — nene2-python

PHP 版 NENE2 との機能同等性を達成し、さらに Python 固有の強みを活かしたフレームワークにする。

---

## 現状（v0.1.0 — 2026-05-19）

### 実装済み ✅
| 領域 | Python 実装 | PHP 対応 |
|---|---|---|
| HTTP コア | `nene2.http` (pagination, problem_details) | `Http/` |
| ミドルウェア | `ErrorHandlerMiddleware` のみ | `Error/ErrorHandlerMiddleware` |
| バリデーション | `ValidationException`, `ValidationError` | `Validation/` |
| 設定 | `AppSettings` (pydantic-settings) | `Config/` |
| Note: 一覧・取得・作成 | UseCase + InMemory repository + Handler | `Example/Note/` 一部 |
| ポリシー | CLAUDE.md, ADR 0001-0004 | 多数 |

### 未実装 ❌（PHP 版比較）

**コア:**
- Database 抽象化層（Interface + SQLite 実装）
- `DomainExceptionHandlerInterface` パターン
- `HealthCheckInterface`
- 構造化ロギング（Monolog → structlog 相当）
- ミドルウェア: SecurityHeaders, RequestId, RequestLogging, RequestSizeLimit
- ミドルウェア: CORS（FastAPI 組み込みを設定）, Rate Limiting
- 認証: `TokenVerifierInterface`, `BearerTokenMiddleware`, `ApiKeyAuthMiddleware`
- MCP: `LocalMcpServer`, `LocalMcpToolCatalog`

**Example:**
- Note: Update, Delete（UseCase + Handler）
- Note: `NoteNotFoundException` + `DomainExceptionHandler`
- Note: UseCase インターフェース (Protocol)
- Note: SQLite repository
- Tag: 全て（フル CRUD + 4 UseCase + 4 Handler + Entity + Exception + Repository）

**Infra:**
- GitHub Actions CI
- Alembic マイグレーション
- `.env.example`
- OpenAPI spec（静的 YAML）

---

## ロードマップ

### v0.2.0 — Write Operations & Domain Exceptions ✅ DONE

**ゴール**: CRUD を完成させ、ドメイン例外パターンを確立する。PHP 版の Note フルセットに追いつく。

- [x] Note: `UpdateNoteUseCase` + `UpdateNoteHandler` (PUT)
- [x] Note: `DeleteNoteUseCase` + `DeleteNoteHandler` (DELETE → 204)
- [x] `NoteNotFoundException` + `DomainExceptionHandlerInterface` パターン実装
- [x] Note: `NoteRepositoryInterface` を Protocol として整備
- [x] Tag: `TagEntity`, `TagRepositoryInterface`, `InMemoryTagRepository`
- [x] Tag: `ListTagsUseCase`, `GetTagUseCase`, `CreateTagUseCase`, `UpdateTagUseCase`, `DeleteTagUseCase`
- [x] Tag: 5 handler (List, Get, Create, Update, Delete)
- [x] `TagNotFoundException`
- [x] `/health` エンドポイント (`HealthCheckInterface` + 基本応答)
- [x] GitHub Actions CI（pytest + mypy + ruff + pip-audit）
- [x] `.env.example`

---

### v0.3.0 — Real Database ✅ DONE

**ゴール**: InMemory を SQLite に差し替えて本番利用可能な状態にする。

- [x] `nene2.database`: `DatabaseQueryExecutorInterface`, `DatabaseTransactionManagerInterface`
- [x] `SqlAlchemyQueryExecutor` 実装
- [x] `SqliteNoteRepository`（CRUD 全操作）
- [x] `SqliteTagRepository`（CRUD 全操作）
- [x] Alembic セットアップ（`alembic init`, initial migration）
- [x] `DatabaseHealthCheck`（接続確認 → `/health` に統合）
- [x] テスト: DB テストを InMemory と SQLite の両方で実行する戦略を確立
- [x] `DB_ADAPTER=sqlite` の場合の環境変数ドキュメント

---

### v0.4.0 — Security & Middleware ✅ DONE

**ゴール**: PHP 版 `Middleware/` と `Log/` に相当する本番グレードのミドルウェアを揃える。

- [x] `SecurityHeadersMiddleware`（X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP）
- [x] `RequestIdMiddleware`（UUID v4 を X-Request-Id に付与）
- [x] `RequestLoggingMiddleware`（structlog で構造化ログ、Request ID を含む）
- [x] `RequestSizeLimitMiddleware`（Body サイズ上限、デフォルト 1MB）
- [x] `ThrottleMiddleware` / `RateLimitMiddleware`（固定ウィンドウ、InMemory ストレージ）
- [x] CORS: FastAPI 組み込みミドルウェアの設定を `AppSettings` から読む
- [x] `structlog` セットアップ（JSON 出力、Request ID 紐付け）
- [x] ADR: ロギング方針（ADR-0005）
- [x] ADR: レート制限設計（ADR-0006）

---

### v0.5.0 — Authentication ✅ DONE

**ゴール**: PHP 版 `Auth/` に相当する認証レイヤーを追加する。

- [x] `TokenVerifierProtocol` (Protocol)
- [x] `BearerTokenMiddleware`（Authorization: Bearer ヘッダーを検証、401 Problem Details）
- [x] `LocalTokenVerifier`（固定トークンセット照合、`secrets.compare_digest` で timing-safe）
- [x] `ApiKeyAuthMiddleware`（X-Api-Key ヘッダー）
- [x] テスト: 認証ありの統合テスト（11テスト）

---

### v1.0.0 — MCP Integration ✅ DONE

**ゴール**: UseCase を MCP ツールとして公開し、AI エージェントがこの API を直接操作できるようにする。

- [x] `nene2.mcp.LocalMcpServer`（FastMCP ラッパー、stdio デフォルト）
- [x] Note UseCase を MCP ツールとして登録（5ツール）
- [x] Tag UseCase を MCP ツールとして登録（5ツール）
- [x] Claude Desktop 設定ガイド (`docs/howto/mcp-setup.md`)
- [x] ADR-0009: MCP 設計方針
- [x] OpenAPI 静的 YAML の出力（`uv run export-openapi`）

---

### v1.x — 同等性完成 & Beyond ✅ DONE

PHP 版追跡・Python 固有の強化:

- [x] Field Trial: Comment ドメインをゼロから実装してフレームワーク検証 (#41)
- [x] MySQL / PostgreSQL repository 実装 (#40)
- [x] 非同期対応: `AsyncUseCaseProtocol` + `nene2.use_case` パッケージ (#42)
- [x] Diátaxis 構造のドキュメント整備（tutorial / howto / explanation / reference）(#43)
- [x] Field Trial 1: InMemory CRUD + git+ インストール検証 (#67)
- [x] Field Trial 2: SQLite 永続化リポジトリ DX 検証 (#72)
- [x] Field Trial 3: Bearer Token 認証 + MCP stdio DX 検証 (#80)
- [ ] Field Trial 4: MCP + SQLite 共有 / ApiKey / CORS 検証
- [ ] PyPI パッケージ公開（FT4 完了後）
- [ ] WebSocket サポート検討

---

## 機能対応表（PHP 版 → Python 版）

| PHP クラス | Python 相当 | 状態 |
|---|---|---|
| `Config/AppConfig` | `nene2.config.AppSettings` | ✅ |
| `Config/AppEnvironment` | `AppSettings.app_env` (str) | ✅ |
| `Error/ErrorHandlerMiddleware` | `nene2.middleware.ErrorHandlerMiddleware` | ✅ |
| `Error/ProblemDetailsResponseFactory` | `nene2.http.problem_details_response()` | ✅ |
| `Error/DomainExceptionHandlerInterface` | `DomainExceptionHandlerProtocol` | ✅ |
| `Http/HealthCheckInterface` | `nene2.http.HealthStatus` + `DatabaseHealthCheck` | ✅ |
| `Http/PaginationQueryParser` | `nene2.http.PaginationQueryParser` | ✅ |
| `Http/PaginationResponse` | `nene2.http.PaginationResponse` | ✅ |
| `Validation/ValidationException` | `nene2.validation.ValidationException` | ✅ |
| `Database/*` | `nene2.database.*` | ✅ |
| `Log/MonologLoggerFactory` | `nene2.log` (structlog) | ✅ |
| `Middleware/SecurityHeadersMiddleware` | `nene2.middleware.SecurityHeadersMiddleware` | ✅ |
| `Middleware/RequestIdMiddleware` | `nene2.middleware.RequestIdMiddleware` | ✅ |
| `Middleware/RequestLoggingMiddleware` | `nene2.middleware.RequestLoggingMiddleware` | ✅ |
| `Middleware/ThrottleMiddleware` | `nene2.middleware.ThrottleMiddleware` | ✅ |
| `Auth/TokenVerifierInterface` | `nene2.auth.TokenVerifierProtocol` | ✅ |
| `Auth/BearerTokenMiddleware` | `nene2.auth.BearerTokenMiddleware` | ✅ |
| `Mcp/LocalMcpServer` | `nene2.mcp.LocalMcpServer` | ✅ |
| `Mcp/LocalMcpToolCatalog` | `example/mcp.py` create_mcp_server() | ✅ |
| `Example/Note` (full CRUD) | `example.note` (全 CRUD) | ✅ |
| `Example/Tag` (full CRUD) | `example.tag` (全 CRUD) | ✅ |
| `Example/Comment` (full CRUD) | `example.comment` (全 CRUD) | ✅ |
| `Example/Health` | `example.health` | ✅ |
| `Auth/TokenIssuerInterface` | `nene2.auth.TokenIssuerProtocol` | ✅ |
| `Auth/TokenVerificationException` | `nene2.auth.TokenVerificationException` | ✅ |
| `Database/DatabaseTransactionManagerInterface` | `nene2.database.DatabaseTransactionManagerInterface` | ✅ |
| `Database/PdoDatabaseTransactionManager` | `nene2.database.SqlAlchemyTransactionManager` | ✅ |
| `Mcp/LocalMcpHttpClientInterface` | `nene2.mcp.McpHttpClientProtocol` | ✅ |
| `Mcp/LocalMcpHttpResponse` | `nene2.mcp.McpHttpResponse` | ✅ |
| `Mcp/NativeLocalMcpHttpClient` | `nene2.mcp.HttpxMcpClient` | ✅ |
| `UseCaseInterface` | `nene2.use_case.UseCaseProtocol[I, O]` | ✅ |
| — | `nene2.use_case.AsyncUseCaseProtocol[I, O]` | ✅ Python 固有 |

---

## Python 固有の優位点（PHP 版より先に進む領域）

- **OpenAPI 自動生成**: FastAPI が Swagger UI / ReDoc を自動提供（PHP は手書き YAML）
- **型安全**: mypy --strict + Pydantic v2 が PHP の PHPStan level 8 より密結合
- **非同期**: `async/await` ネイティブ対応（FastAPI + uvicorn）
- **MCP SDK**: Python 版 MCP SDK が最も充実（Anthropic 公式）
- **Claude Code 統合**: Python コードベースは Claude Code による AI 実装が最も効果的

これらの優位点を活かし、v1.x では PHP 版を超える機能を目指す。
