# CLAUDE.md — nene2-python

NENE2 の設計哲学を Python で実装したリファレンスフレームワーク。
PHP 版 NENE2 (`../NENE2/`) と同一の原則を持ち、Python エコシステムに最適化している。

> **このファイルは AI と人間の両方が読む唯一の真実の源泉 (Single Source of Truth) である。**
> ここに書かれたルールは理由なく変更してはならない。変更する場合は必ず ADR を作成する。

---

## 設計哲学（PHP版 NENE2 と共通）

- **API first**: JSON API と OpenAPI 契約を中心に据える
- **薄い HTTP 層**: ドメインロジックを HTTP・DB から独立させる
- **AI-readable**: 明示的ディレクトリ、小さなクラス、型付き境界、記録された決定
- **LLM delivery ready**: API・MCP・認証・DB・引き継ぎドキュメントを整合させる
- **Security first**: セキュリティは後付けではなく設計の出発点
- **モダン Python**: strict typing、PEP 8、dataclass/Pydantic、自動テスト、静的解析

PHP 版の ADR・設計決定の詳細: `../NENE2/docs/adr/`
フィールドトライアル方法論: `../NENE2/docs/field-trials/`

---

## 1. ワークフロー（常に適用）

- コード変更は **必ず GitHub Issue ベース**
- `main` へ直接コミットしない
- ブランチ命名: `type/issue-number-summary`
- Conventional Commits（type は英語、description は日本語）
- PR 前に **全チェック（後述）を必ず通過**させる

---

## 2. Python コーディング規約

### ベースライン
- Python `>=3.12`（開発環境は 3.14 を使用）
- `from __future__ import annotations` は不要（3.12+ ではネイティブ対応）
- `dataclass(frozen=True, slots=True)` で immutable value object（`slots=True` でメモリ効率化）
- Pydantic BaseModel は **HTTP 境界（リクエストボディ）のみ** 使用

### Python 3.12+ 構文の使用義務

| 用途 | 使うべき構文 | 禁止 |
|---|---|---|
| 型エイリアス | `type X = list[str]` | `X = list[str]`（旧形式） |
| ジェネリクス | `def f[T](x: T) -> T` | `TypeVar('T')` |
| オーバーライド | `@override` | コメントでの注記のみ |
| パターンマッチ | `match` 文 | 長い `if-elif` 連鎖 |
| パス操作 | `pathlib.Path` | `os.path.*` |
| セキュア乱数 | `secrets` モジュール | `random` モジュール |

### 型安全ポリシー

- `Any` は **原則禁止**（mypy --strict で強制）
- `cast()` は最終手段。使う場合は必ず `# reason:` コメントを同行に記述
- `# type: ignore` は **禁止**。どうしても必要な場合は `# type: ignore[specific-code]` とエラーコードを明示し、理由をコメントで残す
- すべての関数・メソッドに引数型・戻り値型注釈（ANN ルールで強制）
- `Protocol` を活用した構造的サブタイピング（ABC と使い分ける）
- `TypedDict` で Dict 構造を型付け（生の `dict[str, Any]` 禁止）

### 命名規則

| 対象 | 規則 | 例 |
|---|---|---|
| クラス | PascalCase | `NoteRepository` |
| 関数・変数 | snake_case | `find_by_id` |
| 定数 | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` |
| プライベート | `_` プレフィックス | `_repository` |
| インターフェース (ABC) | `XxxInterface` | `NoteRepositoryInterface` |
| プロトコル | `XxxProtocol` | `SerializableProtocol` |
| UseCase 入力 DTO | `XxxInput` | `CreateNoteInput` |
| UseCase 出力 DTO | `XxxOutput` | `ListNotesOutput` |
| 例外 | `XxxException` | `ValidationException` |
| エラー明細 | `XxxError` | `ValidationError` |
| Pydantic ボディ | `XxxBody` | `CreateNoteBody` |

**略語禁止**: `mgr`, `ctx`, `val` などは使わない。名前はフル単語で書く。

### サイズ制約（AI 可読性の担保）

| 単位 | 上限 | 超えた場合 |
|---|---|---|
| 1 関数・メソッド | 30 行 | 責務を分割する |
| 1 クラス | 150 行 | モジュールを分割する |
| 1 モジュール (.py) | 300 行 | サブパッケージに切り出す |

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
- ハンドラーは薄く: **parse → use-case → response** の 3 ステップのみ
- UseCase は他の UseCase を呼ばない（オーケストレーションは上位層で行う）

---

## 3. セキュリティポリシー

### 絶対禁止（ruff S ルール + コードレビューで強制）

```python
# 禁止
eval(user_input)
exec(code_string)
pickle.loads(data)               # 外部データのデシリアライズ
subprocess.run(cmd, shell=True)  # シェルインジェクション
os.system(cmd)
random.token_hex(16)             # secrets.token_hex(16) を使う
cursor.execute(f"SELECT * FROM notes WHERE id={id}")  # SQLインジェクション
print(sensitive_data)            # logging モジュールを使う
```

### 必須実装

- **HTTP 境界の全入力を Pydantic で検証**。生の `request.json()` を直接使わない
- **機密フィールドは `SecretStr` 型**（`db_password: SecretStr`）— ログに平文が出力されない
- **文字列フィールドには長さ制限** — `Field(max_length=500)` を必ず設定
- **CORS は許可オリジンを明示**。`allow_origins=["*"]` 禁止（開発環境も含む）
- **セキュリティヘッダーをミドルウェアで付与**（X-Content-Type-Options, X-Frame-Options, etc.）
- **SQL はパラメータ化クエリのみ**。文字列フォーマット禁止
- **ファイルパスは `pathlib.Path` で操作**し、パストラバーサルを防ぐ

### 依存関係の脆弱性スキャン

```bash
uv run pip-audit          # 既知CVEをチェック（CI必須）
```

PR マージ前に `pip-audit` を通過させること。CRITICAL・HIGH の脆弱性がある依存は使用禁止。

---

## 4. テストポリシー

### カバレッジ要件
- **最低 80%**（`pytest --cov-fail-under=80` で CI 強制）
- ドメイン・UseCase 層は **90% 以上** を目標
- HTTP ハンドラーは `TestClient` 経由の統合テストで代替可

### テスト戦略

```
tests/
  nene2/          フレームワークコアの単体テスト
  example/
    note/
      unit/       UseCase・Entity テスト（DB なし・InMemory）
      http/       HTTP ハンドラーテスト（TestClient）
```

- **UseCase / Domain テストは DB なし**で行う（InMemory 実装を使う）
- **DB のモック禁止**（InMemory Repository を実装する）
- **HTTP テストは `TestClient` 経由**（直接関数呼び出し禁止）
- テスト関数名: `test_<動作>_when_<条件>` — 例: `test_returns_404_when_note_not_found`

### テストコードのルール
- `assert` は 1 テスト関数に 1 〜 3 個まで（複数確認は `pytest.mark.parametrize`）
- フィクスチャは `conftest.py` に集約
- `pytest.raises` で例外テストを書く

---

## 5. 依存関係ポリシー

### 追加の判断基準
1. **既存パッケージで代替できないか** を先に確認
2. メンテナンスが活発か（最終リリースが 6ヶ月以内）
3. PyPI のダウンロード数（週 100 万以上を目安）
4. ライセンスが MIT / Apache 2.0 / BSD であること

### 追加手順
1. GitHub Issue で必要性・選定理由を説明
2. `uv add <package>` で追加
3. `uv run pip-audit` で脆弱性チェック
4. PR で ADR に記録（長期的な判断は `docs/adr/` に残す）

### バージョン固定ポリシー
- `pyproject.toml` では `>=X.Y` の下限のみ指定
- `uv.lock` をコミットして完全再現性を保証
- 月次で `uv lock --upgrade` → `pip-audit` → テスト → PR

---

## 6. AI 可読性・MCP 対応ポリシー

AI エージェント（Claude 等）がこのコードベースを正確に理解・操作できることを設計上の要件とする。

### コード設計原則
- **1 ファイル 1 責務**。複数のドメイン概念を同一ファイルに混在させない
- **暗黙の知識をコードに埋め込まない**。ディレクトリ構造と命名で意図を伝える
- **`TYPE_CHECKING` ブロック**で循環インポートを回避しつつ型情報を保つ
- **定数はモジュールレベルで宣言**（`MAX_PAGE_SIZE = 100`）

### OpenAPI・スキーマ
- FastAPI のルート定義には必ず `summary` と `description` を記述
- Pydantic モデルの各フィールドに `description` を記述（`Field(description="...")`)
- レスポンスモデルを `response_model` で明示（`Any` 返却禁止）
- OpenAPI タグでドメイン単位にグループ化

### MCP 対応（実装時）
- UseCase は HTTP ハンドラー非依存のため、MCP ツールとして再利用可能
- `src/nene2/mcp/` 以下に MCP ツール定義を配置
- UseCase の Input/Output が MCP ツールの引数・返り値に直接対応する設計を維持

---

## 7. エラーハンドリングポリシー

- `ValidationException` → 422 validation-failed Problem Details（自動）
- `ErrorHandlerMiddleware` が全例外をキャッチ
- `APP_DEBUG=true` 時のみ例外メッセージを detail に含める
- **スタックトレース・DB 接続情報を公開レスポンスに含めない**
- ログには `logging` モジュールのみ使用（`print()` 禁止）
- 例外を握りつぶす `except Exception: pass` は禁止

---

## 8. HTTP ランタイム・API 設計

- FastAPI + Starlette（ASGI）
- Pydantic v2 でリクエストボディの型検証
- `nene2.http.problem_details_response()` で RFC 9457 エラー応答
- `nene2.http.PaginationQueryParser` でページネーション

### ミドルウェアスタック順序（重要）

`app.add_middleware()` は **LIFO**（後から追加したものが外側になる）。
直感と逆なので注意 — 「外側に置きたいものを後から追加する」。

**推奨 `add_middleware` 呼び出し順**（最初が最内側・最後が最外側）:

```python
# ✅ 正しい順序
app.add_middleware(ErrorHandlerMiddleware)           # 最内側: ハンドラー例外を捕捉
app.add_middleware(RequestLoggingMiddleware)         # ↑
app.add_middleware(ThrottleMiddleware, ...)          # |
app.add_middleware(RequestSizeLimitMiddleware, ...)  # |
app.add_middleware(SecurityHeadersMiddleware)        # ↓  全レスポンスにヘッダー付与
app.add_middleware(RequestIdMiddleware)              # 最外側: 全レスポンスに X-Request-Id 付与
```

```python
# ❌ よくある間違い — ErrorHandler を最後（最外側）に追加
app.add_middleware(RequestIdMiddleware)
app.add_middleware(ErrorHandlerMiddleware)   # 最外側にすると...
# → 500 エラーに X-Request-Id が付かない（内側のミドルウェアをバイパスするため）
# → 500 エラーにセキュリティヘッダーが付かない
```

`ErrorHandlerMiddleware` が例外を捕捉して新しい Response を返すとき、
それより内側のミドルウェアはバイパスされる（Starlette の `BaseHTTPMiddleware` の仕様）。
`RequestIdMiddleware` と `SecurityHeadersMiddleware` は必ず **ErrorHandler より外側** に置くこと。

### REST 規約
- リソース名は複数形: `/notes`, `/tags`
- ID はパスパラメータ: `/notes/{note_id}`
- 一覧は常にページネーション（デフォルト `limit=20`, 最大 `limit=100`）
- 作成は `201 Created` + 作成したリソースを返す
- 削除は `204 No Content`
- 存在しないリソースへの操作は `404 Not Found`（Problem Details）

---

## 9. 開発コマンドリファレンス

```bash
# 依存インストール
uv sync

# 全チェック（CI と同等） — PR 前に必ず通過させること
uv run pytest && \
uv run mypy src/ && \
uv run ruff check src/ tests/ && \
uv run ruff format --check src/ tests/ && \
uv run pip-audit

# 個別
uv run pytest
uv run pytest --tb=short -v
uv run pytest --cov=src --cov-report=html   # HTMLカバレッジレポート
uv run mypy src/
uv run ruff check src/ tests/
uv run ruff check src/ tests/ --fix          # 自動修正
uv run ruff format src/ tests/
uv run pip-audit                             # 依存関係の脆弱性スキャン

# 開発サーバー
uv run uvicorn src.example.app:app --reload --port 8080

# Docker
docker compose up app
```

---

## 10. プロジェクトレイアウト

```
src/
  nene2/              フレームワークコア
    http/             JSON レスポンス・ページネーション・Problem Details
    middleware/       ミドルウェアパイプライン（Error / Security / RequestId / Logging / SizeLimit / Throttle）
    validation/       ValidationException / ValidationError
    config/           型付き設定オブジェクト（AppSettings）
    auth/             TokenVerifierProtocol / BearerTokenMiddleware / ApiKeyAuthMiddleware
    database/         SqlAlchemyQueryExecutor / SqlAlchemyTransactionManager
    mcp/              LocalMcpServer / HttpxMcpClient
    log/              structlog セットアップ
    use_case/         UseCaseProtocol / AsyncUseCaseProtocol
  example/            リファレンス実装
    note/             Note ドメイン（entity / repository / use_case / handler / sqlalchemy_repository）
    tag/              Tag ドメイン（entity / repository / use_case / handler / sqlalchemy_repository）
    comment/          Comment ドメイン（Note に紐付く nested ドメイン）
    app.py            アプリケーションファクトリ
    mcp.py            MCP サーバー（Note / Tag / Comment 全 15 ツール）

tests/                pytest テスト（src/ を鏡像）
docs/
  adr/                設計決定記録（変更理由を残す）
  how-to/             How-to ガイド
  howto/              MCP セットアップガイド
  field-trials/       フィールドトライアル記録（FT1〜FT3）
  tutorials/          チュートリアル
  explanation/        アーキテクチャ解説
  reference/          設定・モジュールリファレンス
  ja/                 日本語ドキュメント（上記すべての翻訳）
.github/workflows/    CI（GitHub Actions）
```

---

## 11. 環境変数

| 変数 | デフォルト | 用途 |
|---|---|---|
| `APP_ENV` | `local` | `local` / `test` / `production` |
| `APP_DEBUG` | `false` | true 時に例外メッセージを 500 detail に含める |
| `APP_NAME` | `nene2-python` | アプリ名 |
| `DB_ADAPTER` | `sqlite` | `sqlite` / `mysql` / `pgsql` |
| `DB_NAME` | `:memory:` | DB 名またはファイルパス |

**シークレット系の環境変数は `.env` ファイルに記述し `.gitignore` で除外する。**
`.env.example` に空の値でキー一覧を記述してコミットする。

---

## 12. PHP版 NENE2 との対応表

| PHP | Python |
|---|---|
| `readonly class` | `dataclass(frozen=True, slots=True)` |
| `ValidationException` + `ValidationError` | 同名クラス（`nene2.validation`） |
| `PaginationQueryParser` | `nene2.http.PaginationQueryParser` |
| `PaginationResponse` | `nene2.http.PaginationResponse` |
| `ProblemDetailsResponseFactory` | `nene2.http.problem_details_response()` |
| `ErrorHandlerMiddleware` | `nene2.middleware.ErrorHandlerMiddleware` |
| `JsonResponseFactory` | `fastapi.responses.JSONResponse` |
| `PHPStan level 8` | `mypy --strict` |
| `PHP-CS-Fixer` | `ruff format` |
| `composer check` | `uv run pytest && mypy && ruff check && ruff format --check && pip-audit` |
