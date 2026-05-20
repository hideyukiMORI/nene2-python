# Changelog

All notable changes to nene2-python are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.8.3] — 2026-05-20

FT31〜FT32 フィールドトライアル — HealthCheck・SecurityHeaders 改善。

### Added
- `HealthStatus.http_status_code` プロパティ — `is_healthy` → 200、それ以外 → 503 のマッピングを提供 (FT31)
- `SecurityHeadersMiddleware` に `permissions_policy: str | None = None` パラメータを追加 (FT32)
- `SecurityHeadersMiddleware` に `hsts: str | None = None` パラメータを追加 (FT32)
- Field trial reports: `docs/field-trials/2026-05-field-trial-31.md`、`docs/field-trials/2026-05-field-trial-32.md`

---

## [1.8.2] — 2026-05-20

FT29〜FT30 フィールドトライアル — AsyncUseCase ドキュメント・RequestLoggingMiddleware 改善。

### Added
- `docs/how-to/async-use-case.md` — `AsyncUseCaseProtocol` + FastAPI `Depends` の DI パターンガイドを追加 (FT29)
- `RequestLoggingMiddleware` に `extra_context: dict[str, str] | None = None` パラメータを追加し、全ログに静的フィールドを付加できるように (FT30)
- Field trial reports: `docs/field-trials/2026-05-field-trial-29.md`、`docs/field-trials/2026-05-field-trial-30.md`

---

## [1.8.1] — 2026-05-20

FT25〜FT28 フィールドトライアル — RequestId ヘルパー・structlog ログレベル・ThrottleMiddleware 改善。

### Added
- `nene2.middleware.get_request_id()` — FastAPI `Depends` で注入できる request ID ヘルパー関数 (FT25)
- `setup_logging()` に `log_level: str = "INFO"` パラメータを追加し `AppSettings.log_level` との統合が容易に (FT26)
- `ThrottleMiddleware` に `path_limits: dict[str, int] | None` パラメータを追加し、パスごとに異なるレート制限を設定可能に (FT28)
- Field trial reports: `docs/field-trials/2026-05-field-trial-25.md` 〜 `docs/field-trials/2026-05-field-trial-28.md`

### Fixed
- `ThrottleMiddleware` — ウィンドウ経過後も `_counts` に古いエントリが残り続ける問題を修正（定期クリーンアップを実装）(FT27)

---

## [1.8.0] — 2026-05-20

FT18〜FT23 フィールドトライアル — ログテスト・Problem Details・ThrottleMiddleware・ドメイン例外・HealthCheck・RequestSizeLimit の各改善。

### Added
- `nene2.log.configure_for_testing()` — structlog を pytest の `caplog` でキャプチャできるように設定するヘルパー関数 (FT18)
- `nene2.http.configure_problem_details(base_url)` — プロジェクト全体のデフォルト `base_url` を一箇所で設定する関数 (FT19)
- `ThrottleMiddleware` — 全レスポンスに `X-RateLimit-Limit`/`Remaining`/`Reset` ヘッダーを付与 (FT20)
- `SimpleDomainHandler` — `exception_class`/`problem_type`/`title`/`status` を渡すだけでドメイン例外ハンドラーを作成できるファクトリクラス (FT21)
- `nene2.http.CompositeHealthCheck` — 複数の `HealthCheckProtocol` を集約するクラス (FT22)
- `HealthCheckProtocol` に `@runtime_checkable` を追加 (FT22)
- Field trial reports: `docs/field-trials/2026-05-field-trial-18.md` 〜 `docs/field-trials/2026-05-field-trial-23.md`
- `docs/how-to/problem-details.md` — Problem Details の使い方ガイドを追加

### Changed
- `RequestLoggingMiddleware` — `exclude_paths: list[str] | None` パラメータを追加（特定パスのログをスキップ可能に）(FT18)
- `ThrottleMiddleware` — 内部の `_is_allowed()` を `_check_rate()` にリネームし、戻り値を `_RateInfo` dataclass に変更 (FT20)
- `RequestSizeLimitMiddleware` — 413 レスポンスに `max_bytes` 構造化フィールドを追加 (FT23)

---

## [1.7.0] — 2026-05-20

FT14〜FT17 フィールドトライアル — プロトコル docstring 改善・ミドルウェアカスタマイズ・DB 例外統一・バグ修正。

### Added
- `SecurityHeadersMiddleware` — `csp: str | None` パラメータで Content-Security-Policy 値をカスタマイズ可能に (FT15)
- `SecurityHeadersMiddleware` — `extra_no_csp_paths: list[str] | None` パラメータでカスタム OpenAPI パスの CSP スキップを設定可能に (FT15)
- `DatabaseIntegrityException` — UNIQUE/FK/CHECK 制約違反時に発生する新例外クラス (FT16)
- Field trial reports: `docs/field-trials/2026-05-field-trial-14.md` 〜 `docs/field-trials/2026-05-field-trial-17.md`

### Changed
- `AsyncUseCaseProtocol` / `UseCaseProtocol` — docstring に `@runtime_checkable` の `isinstance` 制限と `inspect.iscoroutinefunction()` によるランタイム確認方法を明記 (FT14)
- `SqlAlchemyTransactionManager.transactional()` — `IntegrityError` をキャッチして `DatabaseIntegrityException` にラップするよう変更 (FT16)

### Fixed
- `SqlAlchemyQueryExecutor.write()` — `IntegrityError` が `DatabaseIntegrityException` にラップされない不整合を修正 (FT17-F1)
- `SqlAlchemyQueryExecutor.write()` と `_BoundQueryExecutor.write()` — UPDATE/DELETE で 0 行影響した場合に前の INSERT の `lastrowid` が返るバグを修正; INSERT のみ `lastrowid`、UPDATE/DELETE は `rowcount` を返すよう変更 (FT17-F2)

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
