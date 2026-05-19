# ADR-0003: Security First ポリシー

- **Status**: Accepted
- **Date**: 2026-05-19

---

## Context

セキュリティを後付けで実装するプロジェクトは、追加コストが高くなり、見落としが発生しやすい。特に AI エージェントが生成するコードはセキュリティリスクを含む実装パターンを選択する可能性があるため、ルールを明示的に機械強制する必要がある。

---

## Decision

### 1. セキュリティ Lint の機械強制

ruff の `S`（flake8-bandit）ルールを CI で有効化し、以下のパターンを自動検出:

| ルール | 検出内容 |
|---|---|
| S102 | `exec()` の使用 |
| S307 | `eval()` の使用 |
| S301 | `pickle.loads()` の使用 |
| S603, S604 | `subprocess(shell=True)` |
| S311 | `random` モジュールの使用（セキュリティ用途） |
| S608 | SQL 文字列の直接フォーマット |

### 2. 入力バリデーション

すべての HTTP 入力を Pydantic v2 で検証する。

```python
# OK
class CreateNoteBody(BaseModel):
    title: str = Field(max_length=200, description="Note title")
    body: str = Field(max_length=10000, description="Note body")

# NG: 生の dict を直接使用
async def create_note(request: Request) -> JSONResponse:
    data = await request.json()  # 検証なし — 禁止
```

### 3. 機密値の型保護

```python
# OK
class AppSettings(BaseSettings):
    db_password: SecretStr = Field(default=SecretStr(""))

# NG
class AppSettings(BaseSettings):
    db_password: str = ""  # ログに平文が出る
```

`SecretStr` はログ出力時に `**********` でマスクされる。

### 4. CORS 設定

```python
# OK — 許可オリジンを明示
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
)

# NG — ワイルドカード禁止
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

### 5. セキュリティヘッダー

本番環境では以下のヘッダーを全レスポンスに付与する（ミドルウェアで実装）:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'none'
```

### 6. SQL インジェクション防止

```python
# OK — パラメータ化クエリ
cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))

# NG — 文字列フォーマット（S608 で検出）
cursor.execute(f"SELECT * FROM notes WHERE id = {note_id}")
cursor.execute("SELECT * FROM notes WHERE id = " + str(note_id))
```

### 7. 依存関係の脆弱性管理

- `pip-audit` を全チェックコマンドに含める
- CRITICAL / HIGH CVE がある依存はマージ前に解消する
- `uv.lock` をコミットし、サプライチェーン攻撃のリスクを下げる

### 8. ログにシークレットを含めない

```python
# OK
logger.info("DB connection established", extra={"host": settings.db_host})

# NG
logger.info(f"Connecting to DB with password: {settings.db_password}")
```

---

## Consequences

- 新しいエンドポイントを追加する際は Pydantic Body クラスの定義が必須
- `SecretStr` フィールドの値を取り出す際は `.get_secret_value()` が必要（意図的な手間）
- CI が S ルール違反を検出した場合、コードを修正する（ignore を追加しない）
- `tests/**` には `S101`（assert の使用）を例外として許可する
