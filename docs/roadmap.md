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

### v0.2.0 — Write Operations & Domain Exceptions

**ゴール**: CRUD を完成させ、ドメイン例外パターンを確立する。PHP 版の Note フルセットに追いつく。

- [ ] Note: `UpdateNoteUseCase` + `UpdateNoteHandler` (PUT)
- [ ] Note: `DeleteNoteUseCase` + `DeleteNoteHandler` (DELETE → 204)
- [ ] `NoteNotFoundException` + `DomainExceptionHandlerInterface` パターン実装
- [ ] Note: `NoteRepositoryInterface` を Protocol として整備
- [ ] Tag: `TagEntity`, `TagRepositoryInterface`, `InMemoryTagRepository`
- [ ] Tag: `ListTagsUseCase`, `GetTagUseCase`, `CreateTagUseCase`, `UpdateTagUseCase`, `DeleteTagUseCase`
- [ ] Tag: 5 handler (List, Get, Create, Update, Delete)
- [ ] `TagNotFoundException`
- [ ] `/health` エンドポイント (`HealthCheckInterface` + 基本応答)
- [ ] GitHub Actions CI（pytest + mypy + ruff + pip-audit）
- [ ] `.env.example`

**完了定義**: `GET/POST/PUT/DELETE /notes` と `GET/POST/PUT/DELETE /tags` が InMemory で動作し、CI が green になること。

---

### v0.3.0 — Real Database

**ゴール**: InMemory を SQLite に差し替えて本番利用可能な状態にする。

- [ ] `nene2.database`: `DatabaseConnectionInterface`, `DatabaseQueryExecutorInterface`, `DatabaseTransactionManagerInterface`
- [ ] `SqliteDatabaseConnection` 実装
- [ ] `SqliteNoteRepository`（CRUD 全操作）
- [ ] `SqliteTagRepository`（CRUD 全操作）
- [ ] Alembic セットアップ（`alembic init`, initial migration）
- [ ] `DatabaseHealthCheck`（接続確認 → `/health` に統合）
- [ ] テスト: DB テストを InMemory と SQLite の両方で実行する戦略を確立
- [ ] `DB_ADAPTER=sqlite` の場合の環境変数ドキュメント

**完了定義**: `DB_ADAPTER=sqlite DB_NAME=./data/nene2.db` で起動し、Note/Tag の CRUD が永続化されること。

---

### v0.4.0 — Security & Middleware

**ゴール**: PHP 版 `Middleware/` と `Log/` に相当する本番グレードのミドルウェアを揃える。

- [ ] `SecurityHeadersMiddleware`（X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP）
- [ ] `RequestIdMiddleware`（UUID v4 を X-Request-Id に付与）
- [ ] `RequestLoggingMiddleware`（structlog で構造化ログ、Request ID を含む）
- [ ] `RequestSizeLimitMiddleware`（Body サイズ上限、デフォルト 1MB）
- [ ] `ThrottleMiddleware` / `RateLimitMiddleware`（固定ウィンドウ、InMemory ストレージ）
- [ ] CORS: FastAPI 組み込みミドルウェアの設定を `AppSettings` から読む
- [ ] `structlog` セットアップ（JSON 出力、Request ID 紐付け）
- [ ] ADR: ロギング方針（ADR-0005）
- [ ] ADR: レート制限設計（ADR-0006）
- [ ] ADR: PUT vs PATCH ポリシー（ADR-0007）

**完了定義**: `curl -v http://localhost:8080/notes` のレスポンスにセキュリティヘッダーと X-Request-Id が含まれること。

---

### v0.5.0 — Authentication

**ゴール**: PHP 版 `Auth/` に相当する認証レイヤーを追加する。

- [ ] `TokenVerifierInterface` (Protocol)
- [ ] `BearerTokenMiddleware`（Authorization: Bearer ヘッダーを検証、401 Problem Details）
- [ ] `LocalBearerTokenVerifier`（テスト用: 固定トークンを検証）
- [ ] `ApiKeyAuthMiddleware`（X-Api-Key ヘッダー）
- [ ] JWT ライブラリ選定（`python-jose` or `PyJWT`）と ADR-0008
- [ ] Note/Tag ルーターに認証を適用するサンプル
- [ ] テスト: 認証ありの統合テスト

**完了定義**: `Authorization: Bearer <invalid>` で 401、有効トークンで 200 が返ること。

---

### v1.0.0 — MCP Integration

**ゴール**: UseCase を MCP ツールとして公開し、AI エージェントがこの API を直接操作できるようにする。

- [ ] `nene2.mcp.LocalMcpServer`（JSON-RPC 2.0、stdin/stdout）
- [ ] `nene2.mcp.LocalMcpToolCatalog`（`docs/mcp/tools.json` を読み込む）
- [ ] Note UseCase を MCP ツールとして登録
- [ ] Tag UseCase を MCP ツールとして登録
- [ ] `docs/mcp/tools.json`（OpenAPI から自動生成するスクリプト）
- [ ] Claude Desktop / claude MCP クライアント設定例
- [ ] ADR-0009: MCP 設計方針
- [ ] OpenAPI 静的 YAML の出力（`uv run export-openapi`）

**完了定義**: Claude Desktop から MCP 経由で Note の一覧・作成・削除ができること。

---

### v1.x — 同等性完成 & Beyond

PHP 版追跡・Python 固有の強化:

- [ ] Field Trial: AI が新しいドメインをゼロから実装できるか検証
- [ ] MySQL / PostgreSQL repository 実装
- [ ] 非同期対応: `AsyncUseCase` パターン（FastAPI の async を活かす）
- [ ] WebSocket サポート検討
- [ ] Diátaxis 構造のドキュメント整備（tutorial / howto / explanation / reference）
- [ ] PyPI パッケージ公開

---

## 機能対応表（PHP 版 → Python 版）

| PHP クラス | Python 相当 | 状態 |
|---|---|---|
| `Config/AppConfig` | `nene2.config.AppSettings` | ✅ |
| `Config/AppEnvironment` | `AppSettings.app_env` (str) | ✅ |
| `Error/ErrorHandlerMiddleware` | `nene2.middleware.ErrorHandlerMiddleware` | ✅ |
| `Error/ProblemDetailsResponseFactory` | `nene2.http.problem_details_response()` | ✅ |
| `Error/DomainExceptionHandlerInterface` | `DomainExceptionHandlerProtocol` | ❌ v0.2 |
| `Http/HealthCheckInterface` | `nene2.http.HealthCheckInterface` | ❌ v0.2 |
| `Http/PaginationQueryParser` | `nene2.http.PaginationQueryParser` | ✅ |
| `Http/PaginationResponse` | `nene2.http.PaginationResponse` | ✅ |
| `Validation/ValidationException` | `nene2.validation.ValidationException` | ✅ |
| `Database/*` | `nene2.database.*` | ❌ v0.3 |
| `Log/MonologLoggerFactory` | `nene2.log` (structlog) | ❌ v0.4 |
| `Middleware/SecurityHeadersMiddleware` | `nene2.middleware.SecurityHeadersMiddleware` | ❌ v0.4 |
| `Middleware/RequestIdMiddleware` | `nene2.middleware.RequestIdMiddleware` | ❌ v0.4 |
| `Middleware/RequestLoggingMiddleware` | `nene2.middleware.RequestLoggingMiddleware` | ❌ v0.4 |
| `Middleware/ThrottleMiddleware` | `nene2.middleware.ThrottleMiddleware` | ❌ v0.4 |
| `Auth/TokenVerifierInterface` | `nene2.auth.TokenVerifierProtocol` | ❌ v0.5 |
| `Auth/BearerTokenMiddleware` | `nene2.auth.BearerTokenMiddleware` | ❌ v0.5 |
| `Mcp/LocalMcpServer` | `nene2.mcp.LocalMcpServer` | ❌ v1.0 |
| `Mcp/LocalMcpToolCatalog` | `nene2.mcp.LocalMcpToolCatalog` | ❌ v1.0 |
| `Example/Note` (full CRUD) | `example.note` (全 CRUD) | 🔶 一部 |
| `Example/Tag` (full CRUD) | `example.tag` (全 CRUD) | ❌ v0.2 |
| `Example/Health` | `example.health` | ❌ v0.2 |

---

## Python 固有の優位点（PHP 版より先に進む領域）

- **OpenAPI 自動生成**: FastAPI が Swagger UI / ReDoc を自動提供（PHP は手書き YAML）
- **型安全**: mypy --strict + Pydantic v2 が PHP の PHPStan level 8 より密結合
- **非同期**: `async/await` ネイティブ対応（FastAPI + uvicorn）
- **MCP SDK**: Python 版 MCP SDK が最も充実（Anthropic 公式）
- **Claude Code 統合**: Python コードベースは Claude Code による AI 実装が最も効果的

これらの優位点を活かし、v1.x では PHP 版を超える機能を目指す。
