# テストを実行する

## 基本コマンド

```bash
# 全テストを実行（カバレッジ付き）
uv run pytest

# 失敗時の詳細表示
uv run pytest --tb=short -v

# 特定のファイルだけ実行
uv run pytest tests/example/note/

# カバレッジ HTML レポートを生成
uv run pytest --cov=src --cov-report=html
# → htmlcov/index.html をブラウザで開く
```

## テスト構造

```
tests/
  nene2/              フレームワークコアの単体テスト
    use_case/         UseCaseProtocol 準拠テスト
    auth/             認証ミドルウェアとベリファイアー
    database/         TransactionManager テスト
    mcp/              McpHttpClient テスト
    middleware/       各ミドルウェアの単体テスト
  example/
    note/             Note ドメインテスト
      test_list_notes.py          UseCase 単体テスト
      test_note_repository.py     Repository 契約テスト
      test_async_note_use_case.py 非同期 UseCase テスト
    comment/
      test_comment_use_case.py    UseCase 単体テスト（DB なし）
      test_comment_repository.py  InMemory + SQLAlchemy の契約テスト
      test_comment_http.py        HTTP 統合テスト（TestClient）
```

## テストの種類

### UseCase 単体テスト

DB なし・InMemory リポジトリを使用。最も高速。

```python
def test_create_note() -> None:
    repo = InMemoryNoteRepository()
    note = CreateNoteUseCase(repo).execute(CreateNoteInput(title="t", body="b"))
    assert note.title == "t"
```

### Repository 契約テスト

`@pytest.fixture(params=["inmemory", "sqlalchemy"])` で 2 実装を同一テストで検証。

```python
@pytest.fixture(params=["inmemory", "sqlalchemy"])
def repo(request): ...

def test_save_and_find(repo) -> None:
    note = repo.save("title", "body")
    assert repo.find_by_id(note.id) == note
```

### HTTP 統合テスト

FastAPI `TestClient` 経由。ルーター全体を検証。

```python
def test_create_note_returns_201() -> None:
    client = TestClient(create_app(AppSettings(throttle_enabled=False)))
    response = client.post("/notes", json={"title": "t", "body": "b"})
    assert response.status_code == 201
```

### 非同期テスト

`asyncio_mode = "auto"` 設定済みのため `async def test_*` がそのまま動きます。

```python
async def test_async_list_notes() -> None:
    repo = InMemoryNoteRepository()
    result = await AsyncListNotesUseCase(repo).execute(ListNotesInput(limit=10, offset=0))
    assert result.total == 0
```

## カバレッジ要件

- 全体: 80% 以上（CI で強制）
- UseCase / Domain 層: 90% 以上を目標

## 静的解析

```bash
uv run mypy src/          # 型チェック
uv run ruff check src/    # リント
uv run ruff format --check src/ tests/  # フォーマットチェック
uv run pip-audit          # 依存関係の脆弱性スキャン
```
