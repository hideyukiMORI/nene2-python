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
- **XML 処理には `defusedxml` を使用**。標準の `xml.etree.ElementTree` は XXE・展開爆弾に脆弱（FT180 で確認）
  ```bash
  uv add defusedxml
  ```
  `import xml.etree.ElementTree` の代わりに `import defusedxml.ElementTree` を使う。

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
  - `ValidationError` は **`field / message / code` の 3 引数がすべて必須**（省略すると TypeError）
  ```python
  from nene2.validation import ValidationError, ValidationException
  raise ValidationException([
      ValidationError(field="host", message="許可されていません", code="host_not_allowed")
  ])
  ```
- `ErrorHandlerMiddleware` が全例外をキャッチ（FT サンドボックスでも `add_middleware(ErrorHandlerMiddleware)` を忘れないこと）
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

### APIRouter パターン（必須）

すべての FastAPI アプリで `APIRouter` + `create_app()` ファクトリパターンを使うこと。

```python
# ✅ 正しい構造 — app.py
router = APIRouter()

@router.post("/items")  # ← すべてのルート定義は router に紐付ける
def create_item(...): ...

@router.get("/items/{item_id}")
def get_item(...): ...

def create_app() -> FastAPI:          # ← create_app() はファイル末尾に定義する
    application = FastAPI(title="...")
    application.include_router(router)
    return application

app = create_app()                    # ← モジュールレベルの app は最終行
```

**`create_app()` はファイルの末尾**（全 `@router.xxx()` デコレーター定義の後）に置くこと。
先に `app = create_app()` を呼ぶと `router` にルートが登録される前に `include_router()` が実行され、
エンドポイントが空になるバグが発生する（FT182 で発見）。

- `router = APIRouter()` → ファイル先頭の定数・モデル定義の後
- `@router.post(...)` デコレーター → ハンドラー関数の定義
- `create_app()` → ファイル末尾
- `app = create_app()` → ファイル最終行

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
uv run pip-audit --ignore-vuln PYSEC-2025-183

# 個別
uv run pytest
uv run pytest --tb=short -v
uv run pytest --cov=src --cov-report=html   # HTMLカバレッジレポート
uv run mypy src/
uv run ruff check src/ tests/
uv run ruff check src/ tests/ --fix          # 自動修正
uv run ruff format src/ tests/
uv run pip-audit --ignore-vuln PYSEC-2025-183  # 依存関係の脆弱性スキャン（CI と同じ）

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
    http/             JSON レスポンス・ページネーション・Problem Details・ETag・query ヘルパー
    middleware/       ミドルウェアパイプライン + setup_middlewares()
    validation/       ValidationException / ValidationError
    config/           型付き設定オブジェクト（AppSettings）
    auth/             Bearer / API Key / CompositeAuth / LocalTokenIssuer
    cache/            TtlCache[V]
    security/         verify_hmac_signature()
    database/         SqlAlchemyQueryExecutor / SqlAlchemyTransactionManager
    mcp/              LocalMcpServer / HttpxMcpClient
    log/              structlog セットアップ
    use_case/         UseCaseProtocol / AsyncUseCaseProtocol
  example/            リファレンス実装
    note/             Note ドメイン（entity / repository / use_case / handler / sqlalchemy_repository）
    tag/              Tag ドメイン（entity / repository / use_case / handler / sqlalchemy_repository）
    comment/          Comment ドメイン（Note に紐付く nested ドメイン）
    app.py            アプリケーションファクトリ（create_app）
    mcp.py            MCP サーバー（Note / Tag / Comment 全 15 ツール）

tests/                pytest テスト（src/ を鏡像、466 tests）
docs/
  adr/                設計決定記録（変更理由を残す）
  how-to/             How-to ガイド（24+ 本）
  howto/              MCP セットアップガイド
  field-trials/       フィールドトライアル記録（FT1〜FT219+、INDEX.md 参照）
  field-trials/INDEX.md  FT 検索索引（テーマ・診断種別・Follow-up Issue）
  todo/current.md     現状サマリー・次タスク
  roadmap.md          ロードマップ・PHP 版対応表
  review/             作業日報
  tutorials/          チュートリアル
  explanation/        アーキテクチャ解説
  reference/          設定・モジュールリファレンス
  ja/                 日本語ドキュメント（上記すべての翻訳）
.github/workflows/    CI（GitHub Actions: Python 3.12 / 3.14）
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

## 12. フィールドトライアル（FT）方法論

### 目的

Python 標準ライブラリ・サードパーティライブラリを nene2-python 上で実装し、
フレームワーク API の安定性を実装者目線で検証する。
「実際に詰まったポイント」だけを観察ベースで Issue 化し、
ドキュメントと設計を同時に成長させるサイクルを回す。

### フロー（1 FT あたり）

```
1. テーマ選定（docs/todo/current.md から未検証パターンを選ぶ）
2. 独立サンドボックスを作成
   場所: /home/xi/docker/nene2-python-FT/ftNNN-テーマ名/
   ゼロから uv init → nene2-python を依存として追加
3. 実装 + 全チェック通過
   uv run pytest && uv run mypy src/ && uv run ruff check src/ tests/
4. 摩擦点を記録（F-1, F-2, ...）
5. FT レポート作成 → docs/field-trials/2026-05-field-trial-NNN.md
   テンプレート: docs/templates/field-trial-report.md
6. DX Review（6ペルソナ）を実施（後述）
7. FT番号が3の倍数なら セキュリティ診断 を実施（後述）
8. Follow-up Issues をその場で修正してからクローズする
   - 発見した問題（摩擦点・セキュリティ指摘）は FT PR に含めて修正する
   - 修正 → テスト全通過 → PR に含める → GitHub Issue は PR 内でクローズ（Closes #NNN）
   - CLAUDE.md 追記・docs 更新・サンドボックスのコード修正すべてを同じ PR に含める
   - 「外部依存の修正待ち」など対応不可能な理由がある場合のみ Issue を残し、理由を PR 説明に記載する
9. まとめて main merge → パッチバージョン（v1.8.N）でリリース
```

### DX Review — 6ペルソナ

各 FT レポートの末尾に、以下 6 ペルソナ目線での評価を必ず記載する。
「コードが動く」だけでなく「初心者から経験者まで安全に使えるか」を客観的に検証する。

| ペルソナ | 属性 | 主な評価観点 |
|---|---|---|
| **1. 初心者** | Python 歴1年・独学中・女性・バックエンド志望 | ドキュメント理解・事故リスク・規約の使いやすさ |
| **2. ロースキル経験者** | Python 歴3-4年・スクリプト系・男性・SES | コピペ可能性・拡張時の罠・セキュリティ的な事故リスク |
| **3. フロントエンド寄り** | React/TS 歴4年・バックエンド転向中・ノンバイナリ | エラーレスポンスの質・Python 固有概念の学習コスト |
| **4. バックエンド経験者** | Django/FastAPI 歴5-6年・男性・リードエンジニア | 他フレームワークとの差異・nene2 の薄さへの評価 |
| **5. シニアエンジニア** | 設計・コードレビュー担当・女性・10-12年 | コードレビューチェックポイント・チームでの安全なパターン |
| **6. 設計者** | nene2-python 設計ポリシー目線 | CLAUDE.md ポリシー整合性・初心者でも安全な API 達成度 |

各ペルソナの記述フォーマット:
- 状況説明 1 文（ペルソナが置かれているコンテキスト）
- 太字サブヘッディング 2〜4個（ドキュメント理解 / 事故リスク / 規約の使いやすさ など）
- 事故リスクは「高 / 中 / 低」で定性評価

### セキュリティ診断（3の倍数 FT）

**FT番号 % 3 == 0 のとき**（FT165, FT168, ...）、通常のFT完了後に追加で実施する。

**診断レベル**: Django・FastAPI・SQLAlchemy 本体でも CVE が報告されてきた攻撃ベクターを対象とする。

対象カテゴリ（詳細は `docs/templates/field-trial-report.md` のセキュリティ診断セクション参照）:

1. **OWASP API Security Top 10 (2023)** — BOLA/IDOR・認証破損・Mass Assignment・リソース消費・SSRF・設定ミス
2. **インジェクション攻撃** — SQL・コマンド・パストラバーサル・SSTI・HTTP ヘッダーインジェクション
3. **認証・認可** — パスワードハッシュ・タイミング攻撃・JWT alg:none・セッション固定
4. **入力バリデーション** — 上限なし文字列・数値オーバーフロー・Null バイト・Unicode RTL
5. **情報漏洩** — スタックトレース公開・ログへの機密データ出力・pip-audit CVE スキャン
6. **Python/FastAPI 固有** — ReDoS・pickle/yaml インジェクション・非同期レースコンディション・Pydantic 型強制・SQLAlchemy raw query バイパス

**合否判定**:
- **合格**: 全カテゴリ問題なし
- **条件付き合格**: MEDIUM 以下の指摘のみ → **同 FT の PR 内で修正してからマージ**
- **不合格**: HIGH/CRITICAL の指摘あり → main merge 前に必須修正

---

## 13. PHP版 NENE2 との対応表

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
| `composer check` | `uv run pytest && mypy && ruff check && ruff format --check && pip-audit --ignore-vuln PYSEC-2025-183` |
