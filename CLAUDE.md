# CLAUDE.md — nene2-python

NENE2 の設計哲学を Python で実装したリファレンスフレームワーク。
PHP 版 NENE2 (`../NENE2/`) と同一の原則を持ち、Python エコシステムに最適化している。

---

## 設計哲学（PHP版 NENE2 と共通）

- **API first**: JSON API と OpenAPI 契約を中心に据える
- **薄い HTTP 層**: ドメインロジックを HTTP・DB から独立させる
- **AI-readable**: 明示的ディレクトリ、小さなクラス、型付き境界、記録された決定
- **LLM delivery ready**: API・MCP・認証・DB・引き継ぎドキュメントを整合させる
- **モダン Python**: strict typing、PEP 8、dataclass/Pydantic、自動テスト、静的解析

PHP 版の ADR・設計決定の詳細: `../NENE2/docs/adr/`
フィールドトライアル方法論: `../NENE2/docs/field-trials/`

---

## 1. ワークフロー（常に適用）

- コード変更は **必ず GitHub Issue ベース**
- `main` へ直接コミットしない
- ブランチ命名: `type/issue-number-summary`
- Conventional Commits（type は英語、description は日本語）

---

## 2. Python コーディング規約

### ベースライン
- Python `>=3.12`
- `from __future__ import annotations` は不要（3.12+ ではネイティブ対応）
- `dataclass(frozen=True)` で immutable value object
- Pydantic BaseModel は HTTP 境界（リクエストボディ）のみ使用

### アーキテクチャ
```
HTTP Handler (FastAPI router)
  ↓ calls
UseCase          ← ビジネスロジック、HTTP・DB 知識なし
  ↓ calls
RepositoryInterface ← ABC で定義
  ↓ implemented by
ConcreteRepository   ← SQLite / MySQL / In-memory
```

- UseCase / Domain は FastAPI・SQLAlchemy から独立させる
- コンストラクタインジェクションを優先（FastAPI の Depends は HTTP 境界のみ）
- ハンドラーは薄く: parse → use-case → response

### HTTP ランタイム
- FastAPI + Starlette（ASGI）
- Pydantic v2 でリクエストボディの型検証
- `nene2.http.problem_details_response()` で RFC 9457 エラー応答
- `nene2.http.PaginationQueryParser` でページネーション

### エラーハンドリング
- `ValidationException` → 422 validation-failed Problem Details（自動）
- `ErrorHandlerMiddleware` が全例外をキャッチ
- `APP_DEBUG=true` 時のみ例外メッセージを detail に含める
- スタックトレース・DB 接続情報を公開レスポンスに含めない

### テスト
- `pytest` + `httpx` + `fastapi.testclient.TestClient`
- UseCase / Domain のテストは DB なしで行う（InMemory 実装を使う）
- HTTP テストは `TestClient` 経由で行う

---

## 3. 開発コマンドリファレンス

```bash
# 依存インストール
uv sync

# 全チェック（CI と同等）
uv run pytest && uv run mypy src/ && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/

# 個別
uv run pytest
uv run pytest --tb=short -v
uv run mypy src/
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# 開発サーバー
uv run uvicorn src.example.app:app --reload --port 8080

# Docker
docker compose up app
```

---

## 4. プロジェクトレイアウト

```
src/
  nene2/              フレームワークコア
    http/             JSON レスポンス・ページネーション・Problem Details
    middleware/       ミドルウェアパイプライン
    validation/       ValidationException / ValidationError
    config/           型付き設定オブジェクト（AppSettings）
    mcp/              MCP サーバー（未実装）
  example/            リファレンス実装
    note/             Note ドメイン (entity / repository / use_case / handler)
    tag/              Tag ドメイン（未実装）
    app.py            アプリケーションファクトリ

tests/                pytest テスト（src/ を鏡像）
docs/
  adr/                設計決定記録
  howto/              How-to ガイド
  field-trials/       AI 実装検証記録
.github/workflows/    CI（GitHub Actions）
```

---

## 5. 環境変数

| 変数 | デフォルト | 用途 |
|---|---|---|
| `APP_ENV` | `local` | `local` / `test` / `production` |
| `APP_DEBUG` | `false` | true 時に例外メッセージを 500 detail に含める |
| `APP_NAME` | `nene2-python` | アプリ名 |
| `DB_ADAPTER` | `sqlite` | `sqlite` / `mysql` / `pgsql` |
| `DB_NAME` | `:memory:` | DB 名またはファイルパス |

---

## 6. PHP版 NENE2 との対応表

| PHP | Python |
|---|---|
| `readonly class` | `dataclass(frozen=True)` |
| `ValidationException` + `ValidationError` | 同名クラス（`nene2.validation`） |
| `PaginationQueryParser` | `nene2.http.PaginationQueryParser` |
| `PaginationResponse` | `nene2.http.PaginationResponse` |
| `ProblemDetailsResponseFactory` | `nene2.http.problem_details_response()` |
| `ErrorHandlerMiddleware` | `nene2.middleware.ErrorHandlerMiddleware` |
| `JsonResponseFactory` | `fastapi.responses.JSONResponse` |
| `PHPStan level 8` | `mypy --strict` |
| `PHP-CS-Fixer` | `ruff format` |
| `composer check` | `uv run pytest && mypy && ruff check && ruff format --check` |
