# 新しいドメインを追加する

既存の Note・Tag・Comment ドメインと同じパターンで新しいドメインを追加するチェックリストです。

## チェックリスト

### 1. ドメインパッケージを作成する

```bash
mkdir -p src/example/<domain>
touch src/example/<domain>/__init__.py
```

### 2. 各ファイルを作成する

| ファイル | 内容 |
|---|---|
| `entity.py` | `@dataclass(frozen=True, slots=True)` でエンティティを定義 |
| `repository.py` | `XxxRepositoryInterface(ABC)` + `InMemoryXxxRepository` |
| `exceptions.py` | `XxxNotFoundException` + `XxxNotFoundExceptionHandler` |
| `use_case.py` | 5 UseCase (List / Get / Create / Update / Delete) + Input/Output DTO |
| `handler.py` | `make_xxx_router()` — parse → use-case → response |
| `sqlalchemy_repository.py` | SQL バックエンド実装 |

### 3. schema.py にテーブルを追加する

`src/example/schema.py` の `ensure_schema()` にテーブル定義を追加します。

```python
executor.write(
    "CREATE TABLE IF NOT EXISTS your_domain ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "name TEXT NOT NULL,"
    "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
    ")"
)
```

### 4. app.py に組み込む

`src/example/app.py` の `_build_repositories()` と `create_app()` を更新します。

```python
# _build_repositories() の戻り値に追加
your_repo = SqlAlchemyYourRepository(executor)

# create_app() でルーターを登録
app.include_router(make_your_router(
    list_use_case=ListYourUseCase(your_repo),
    ...
))
```

### 5. テストを書く

```
tests/example/<domain>/
  __init__.py
  test_<domain>_use_case.py     # UseCase 単体テスト（DB なし）
  test_<domain>_repository.py   # Repository 契約テスト（InMemory + SQLAlchemy）
  test_<domain>_http.py         # HTTP 統合テスト（TestClient）
```

### 6. MCP ツールに追加する（任意）

`src/example/mcp.py` の `create_mcp_server()` に UseCase を登録します。

### 7. 全チェックを通過させる

```bash
uv run pytest && \
uv run mypy src/ && \
uv run ruff check src/ tests/ && \
uv run ruff format --check src/ tests/
```

## 命名規則

- エンティティクラス: `PascalCase` (`Note`, `Tag`, `Comment`)
- UseCase 入力 DTO: `XxxInput` (`CreateNoteInput`)
- 例外: `XxxNotFoundException`
- ハンドラーファクトリ: `make_xxx_router()`

## 参考実装

- `src/example/note/` — 基本的な CRUD ドメイン
- `src/example/comment/` — 外部キー (note_id) を持つネストドメイン
