# Changelog

All notable changes to nene2-python are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.8.32] — 2026-05-20

FT99 フィールドトライアル — Webhook HMAC-SHA256 署名検証パターン検証と nene2.security モジュール追加。

### Added
- `nene2.security` モジュールを新設 (#404) (FT99)
  - `verify_hmac_signature(body, secret, signature, *, prefix="")` — GitHub/Stripe 方式の Webhook HMAC-SHA256 署名を timing-safe に検証
  - `hmac.compare_digest()` による timing attack 対策済み
- Field trial report: `docs/field-trials/2026-05-field-trial-99.md` (FT99)

---

## [1.8.31] — 2026-05-20

FT97 フィールドトライアル — HTTP キャッシュヘッダーパターン検証と generate_etag() 追加。

### Added
- `nene2.http.generate_etag(data)` — ETag 生成ユーティリティ関数を追加 (#397) (FT97)
  — dict / list / str / bytes から RFC 9110 形式の ETag 文字列を生成
  — HTTP キャッシュ (`If-None-Match` / `304 Not Modified`) パターンで利用
- Field trial reports: `docs/field-trials/2026-05-field-trial-92.md` 〜 `2026-05-field-trial-97.md` (FT92〜FT97)

---

## [1.8.30] — 2026-05-20

FT87 フィールドトライアル — カスタムレスポンスヘッダーパターン検証と problem_details_response() 改善。

### Added
- `problem_details_response()` に `headers: dict[str, str] | None = None` パラメーターを追加 (#369) (FT87)
  — エラーレスポンスに `Retry-After`（429）、`WWW-Authenticate`（401）などのカスタムヘッダーを付与可能に
- Field trial reports: `docs/field-trials/2026-05-field-trial-85.md`, `2026-05-field-trial-86.md`, `2026-05-field-trial-87.md` (FT85, FT86, FT87)

---

## [1.8.29] — 2026-05-20

FT84 フィールドトライアル — 認証 Depends ユーティリティ検証と make_require_auth() 追加。

### Added
- `nene2.auth` に `make_require_auth(verifier)` Depends ファクトリーを追加 (#359) (FT84)
  — `TokenVerifierProtocol` を FastAPI の `Depends` に接続するボイラープレートを解消
  — 有効トークンで token 文字列を返し、未認証・無効トークンで 401 を raise
- Field trial report: `docs/field-trials/2026-05-field-trial-84.md` (FT84)

---

## [1.8.28] — 2026-05-20

FT83 フィールドトライアル — Depends() DI パターン検証と PaginationResponse / PaginationDep 改善。

### Added
- `PaginationResponse.model_dump()` を `to_dict()` の Pydantic 互換エイリアスとして追加 (#355) (FT83)
  — Pydantic v2 ユーザーが `model_dump()` を期待して AttributeError になる問題を解消
- `PaginationDep` 型エイリアスを `nene2.http` に追加 (#355) (FT83)
  — `Annotated[PaginationQueryParser, Depends(PaginationQueryParser)]` の省略形
- Field trial report: `docs/field-trials/2026-05-field-trial-83.md` (FT83)

---

## [1.8.27] — 2026-05-20

FT81 フィールドトライアル — CORS 設定パターン検証と setup_middlewares() への CORS 統合。

### Added
- `setup_middlewares()` に `cors_allowed_origins` / `cors_allow_credentials` / `cors_allow_methods` / `cors_allow_headers` パラメーターを追加 (#348) (FT81)
  — `CORSMiddleware` を最外側に自動配置し、OPTIONS プリフライトが確実に処理される
  — `cors_allowed_origins=["*"]` を渡すと `ValueError` を raise（wildcard 禁止ポリシーの実装強制）
- Field trial report: `docs/field-trials/2026-05-field-trial-81.md` (FT81)

---

## [1.8.26] — 2026-05-20

FT80 フィールドトライアル — LocalMcpServer + HttpxMcpClient MCP E2E 検証と list_tools() 追加。

### Added
- `LocalMcpServer` に `list_tools()` メソッドを追加 (#342) (FT80)
  — 登録済みツール名の一覧を返す。デバッグ・イントロスペクション用途
- Field trial report: `docs/field-trials/2026-05-field-trial-80.md` (FT80)

---

## [1.8.25] — 2026-05-20

FT79 フィールドトライアル — RequestLoggingMiddleware の構造化ログ検証と context_extractor 追加。

### Added
- `RequestLoggingMiddleware` に `context_extractor` コールバックパラメーターを追加 (#339) (FT79)
  — リクエストごとの動的なログコンテキスト（user_id、テナントID等）を注入できる
- Field trial report: `docs/field-trials/2026-05-field-trial-79.md` (FT79)

---

## [1.8.24] — 2026-05-20

FT78 フィールドトライアル — ThrottleMiddleware の境界動作検証とドキュメント強化。

### Changed
- `ThrottleMiddleware` クラス docstring に Fixed Window バースト特性とマルチプロセス非対応の警告を追記 (#335) (FT78)
- `setup_middlewares()` の `throttle_limit` docstring にマルチプロセス警告を追記 (#335) (FT78)
- Field trial report: `docs/field-trials/2026-05-field-trial-78.md` (FT78)

---

## [1.8.23] — 2026-05-20

FT77 フィールドトライアル — BearerToken + ApiKey 混在認証と include_paths 追加。

### Added
- `BearerTokenMiddleware` / `ApiKeyAuthMiddleware` に `include_paths` パラメーターを追加 (#331) (FT77)
  — プレフィックスマッチで「守りたいパス」を直接指定でき、混在認証の `exclude_paths` 二重管理を解消
- Field trial report: `docs/field-trials/2026-05-field-trial-77.md` (FT77)

---

## [1.8.22] — 2026-05-20

FT76 フィールドトライアル — async def + sync DB ブロッキング問題と run_in_threadpool 追加。

### Added
- `run_in_threadpool` を `nene2.use_case` から re-export (#326) (FT76)
  — Starlette の `run_in_threadpool` を nene2 公開 API として公開し、
  `async def` ハンドラーから同期 DB 処理を安全にスレッドプールへオフロードできる
- Field trial report: `docs/field-trials/2026-05-field-trial-76.md` (FT76)

---

## [1.8.21] — 2026-05-20

FT75 フィールドトライアル — ミドルウェアスタック順序問題の発見と根本解決。

### Added
- `setup_middlewares(app, ...)` ユーティリティ関数を追加 (#320 #321) (FT75)
  — 全ミドルウェアを正しい順序（RequestId 最外側・ErrorHandler 最内側）で一括登録し、
  エラーレスポンスにも X-Request-Id とセキュリティヘッダーが確実に付与される
- `docs/how-to/middleware-stack.md` — ミドルウェア順序の解説ガイドを追加
- CLAUDE.md セクション 8 に推奨 `add_middleware` 順序を追記
- Field trial report: `docs/field-trials/2026-05-field-trial-75.md` (FT75)

---

## [1.8.20] — 2026-05-20

FT72 フィールドトライアル — DatabaseIntegrityException + ErrorHandlerMiddleware.install() 改善。

### Added
- `ErrorHandlerMiddleware.install(app)` クラスメソッドを追加 (#315) (FT72)
  — `add_middleware` と `add_exception_handler(RequestValidationError)` を一度に設定し、
  Pydantic の 422 バリデーションエラーも nene2 Problem Details 形式に自動統一する
- Field trial reports: `docs/field-trials/2026-05-field-trial-70.md` 〜 `2026-05-field-trial-72.md` (FT70〜FT72)

---

## [1.8.19] — 2026-05-20

FT68 フィールドトライアル — SimpleDomainHandler + extra_factory 実運用検証。

### Changed
- `problem_details_response` の docstring に `extra` がトップレベルにフラットマージされることを明記 (#308) (FT68)
- `SimpleDomainHandler` の docstring に `extra_factory` のフラットマージ動作を例示 (#308) (FT68)

### Added
- Field trial report: `docs/field-trials/2026-05-field-trial-68.md`

---

## [1.8.18] — 2026-05-20

FT67 フィールドトライアル — SqlAlchemyTransactionManager 実運用検証。

### Changed
- `SqlAlchemyQueryExecutor` の docstring に SQLite `:memory:` + `StaticPool` の注意書きを追加 (#305) (FT67)

### Added
- Field trial reports: `docs/field-trials/2026-05-field-trial-65.md` 〜 `2026-05-field-trial-67.md` (FT65〜FT67)

---

## [1.8.17] — 2026-05-20

FT64 フィールドトライアル — ValidationException 複数エラー実運用検証。

### Fixed
- `ValidationError.code` にスペースが含まれる場合 `ValueError` を発生させるよう修正 — `message` と `code` の混同を早期検出できるようになった (#300) (FT64)

### Changed
- `ValidationError` と `ValidationException.single()` の docstring を改善 — `message` (人間可読) と `code` (機械可読 snake_case) の違いをキーワード引数付き例で明示 (#300) (FT64)

### Added
- Field trial report: `docs/field-trials/2026-05-field-trial-64.md`

---

## [1.8.16] — 2026-05-20

FT63 フィールドトライアル — configure_problem_details 実運用検証 + PROBLEM_DETAILS_BASE_URL エクスポート修正。

### Fixed
- `PROBLEM_DETAILS_BASE_URL` 定数を `nene2.http` からエクスポートするよう修正 — テストで `from nene2.http import PROBLEM_DETAILS_BASE_URL` が利用可能になった (#296) (FT63)

### Added
- Field trial reports: `docs/field-trials/2026-05-field-trial-56.md` 〜 `2026-05-field-trial-63.md` (FT56〜FT63)

---

## [1.8.15] — 2026-05-20

FT55 フィールドトライアル — parse_db_datetime 実運用検証。

### Added
- Field trial report: `docs/field-trials/2026-05-field-trial-55.md`

---

## [1.8.14] — 2026-05-20

FT54 フィールドトライアル — RequestSizeLimitMiddleware + path_limits 実運用検証。

### Added
- Field trial report: `docs/field-trials/2026-05-field-trial-54.md`

---

## [1.8.13] — 2026-05-20

FT53 フィールドトライアル — ApiKeyAuthMiddleware 実運用検証 + header_name パラメータ追加。

### Added
- `ApiKeyAuthMiddleware` に `header_name: str = "X-Api-Key"` パラメータを追加 — カスタムヘッダー名 (`X-Service-Token` 等) を指定可能に。エラーメッセージにも `header_name` が反映される (#286) (FT53)
- Field trial report: `docs/field-trials/2026-05-field-trial-53.md`

---

## [1.8.12] — 2026-05-20

FT52 フィールドトライアル — ミドルウェアスタック組み合わせ検証 + LocalTokenVerifier 改善。

### Changed
- `LocalTokenVerifier.__init__` — `allowed_tokens` の型を `list[str] | set[str] | frozenset[str]` に変更。内部で `frozenset` に変換し `in` 演算が O(1) になった (#284) (FT52)

### Added
- Field trial report: `docs/field-trials/2026-05-field-trial-52.md`

---

## [1.8.11] — 2026-05-20

FT51 フィールドトライアル — SimpleDomainHandler 実運用検証 + problem_details_response バグ修正。

### Fixed
- `problem_details_response()` — `extra` に RFC 9457 予約済みフィールド (`type`, `title`, `status`, `detail`) が含まれる場合に `ValueError` を raise するよう修正 (#282) (FT51)

### Added
- Field trial report: `docs/field-trials/2026-05-field-trial-51.md`

---

## [1.8.10] — 2026-05-20

FT50 フィールドトライアル — ValidationException + ValidationCode(StrEnum) 実運用検証。

### Added
- Field trial report: `docs/field-trials/2026-05-field-trial-50.md`

---

## [1.8.9] — 2026-05-20

FT46〜FT49 フィールドトライアル — ドキュメント改善。

### Added
- Field trial reports: `docs/field-trials/2026-05-field-trial-46.md` 〜 `docs/field-trials/2026-05-field-trial-49.md`

### Changed
- `docs/how-to/run-tests.md` — SQLite 外部キー制約 (`PRAGMA foreign_keys=ON`) の注意事項を追記 (FT46)

---

## [1.8.8] — 2026-05-20

FT45 フィールドトライアル — SecurityHeadersMiddleware CSP バグ修正。

### Fixed
- `SecurityHeadersMiddleware` — `csp=""` を渡したとき空の `Content-Security-Policy` ヘッダーが付与される問題を修正。`csp=""` の場合は CSP ヘッダーを付与しないよう変更 (#271) (FT45)

### Added
- Field trial report: `docs/field-trials/2026-05-field-trial-45.md`

---

## [1.8.7] — 2026-05-20

FT43〜FT44 フィールドトライアル — ThrottleMiddleware path_limits 確認・PaginationQueryParser バリデーション改善。

### Added
- `nene2.middleware.request_validation_error_handler` を公開エクスポートに追加 — FastAPI の `RequestValidationError` を Problem Details 形式に変換するハンドラーを `from nene2.middleware import request_validation_error_handler` でアクセス可能に (FT44)
- Field trial reports: `docs/field-trials/2026-05-field-trial-43.md`、`docs/field-trials/2026-05-field-trial-44.md`

---

## [1.8.6] — 2026-05-20

FT41〜FT42 フィールドトライアル — structlog テスト統合ドキュメント・configure_problem_details リセット関数。

### Added
- `nene2.http.reset_problem_details()` — `configure_problem_details()` で設定したグローバル状態をテスト間でリセットするヘルパー関数 (FT42)
- Field trial reports: `docs/field-trials/2026-05-field-trial-41.md`、`docs/field-trials/2026-05-field-trial-42.md`

### Changed
- `docs/how-to/run-tests.md` — `configure_for_testing()` + `caplog` による structlog ログキャプチャパターンを追記 (FT41)

---

## [1.8.5] — 2026-05-20

FT37〜FT40 フィールドトライアル — RequestSizeLimitMiddleware パスごとサイズ制限とドキュメント改善。

### Added
- `RequestSizeLimitMiddleware` に `path_limits: dict[str, int] | None = None` パラメータを追加 — パスごとに異なるリクエストボディサイズ制限を設定可能に (FT39)
- Field trial reports: `docs/field-trials/2026-05-field-trial-37.md` 〜 `docs/field-trials/2026-05-field-trial-40.md`

---

## [1.8.4] — 2026-05-20

FT33〜FT36 フィールドトライアル — バリデーション・DB整合性・混合認証・非同期ヘルスチェック改善。

### Added
- `AsyncHealthCheckProtocol` — `async def check() -> HealthStatus` の Protocol (FT36)
- `AsyncCompositeHealthCheck` — 複数の非同期ヘルスチェックを `asyncio.gather` で並列実行して集約するクラス (FT36)
- `docs/how-to/validation.md` — `ValidationCode(StrEnum)` パターンと複数フィールドバリデーションの how-to ガイドを追加 (FT33)
- Field trial reports: `docs/field-trials/2026-05-field-trial-33.md` 〜 `docs/field-trials/2026-05-field-trial-36.md`

### Changed
- `docs/how-to/run-tests.md` — インメモリ SQLite テスト用 `StaticPool` パターンを追記 (FT34)
- `docs/how-to/configure-auth.md` — AND / OR 条件の違いと `EitherOrAuthMiddleware` パターンを追記 (FT35)

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
