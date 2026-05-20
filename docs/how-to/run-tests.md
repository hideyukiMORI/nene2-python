# Run tests

## Basic commands

```bash
# Run all tests with coverage
uv run pytest

# Verbose output on failure
uv run pytest --tb=short -v

# Run a specific directory
uv run pytest tests/example/note/

# Generate an HTML coverage report
uv run pytest --cov=src --cov-report=html
# → open htmlcov/index.html in your browser
```

## Test layout

```
tests/
  nene2/              Framework core unit tests
    use_case/         UseCaseProtocol compliance
    auth/             Auth middleware and verifiers
    database/         TransactionManager tests
    mcp/              McpHttpClient tests
    middleware/       Each middleware in isolation
  example/
    note/             Note domain tests
      test_list_notes.py           UseCase unit tests
      test_note_repository.py      Repository contract tests
      test_async_note_use_case.py  Async UseCase tests
    comment/
      test_comment_use_case.py     UseCase unit tests (no DB)
      test_comment_repository.py   InMemory + SQLAlchemy contract tests
      test_comment_http.py         HTTP integration tests (TestClient)
```

## Test types

### UseCase unit tests

No database, no HTTP — use InMemory repositories. Fastest.

```python
def test_create_note() -> None:
    repo = InMemoryNoteRepository()
    note = CreateNoteUseCase(repo).execute(CreateNoteInput(title="t", body="b"))
    assert note.title == "t"
```

### Repository contract tests

`@pytest.fixture(params=["inmemory", "sqlalchemy"])` runs the same assertions against both implementations.

```python
@pytest.fixture(params=["inmemory", "sqlalchemy"])
def repo(request): ...

def test_save_and_find(repo) -> None:
    note = repo.save("title", "body")
    assert repo.find_by_id(note.id) == note
```

### HTTP integration tests

Use FastAPI's `TestClient`. Tests the full stack from HTTP to repository.

```python
def test_create_note_returns_201() -> None:
    client = TestClient(create_app(AppSettings(throttle_enabled=False)))
    response = client.post("/notes", json={"title": "t", "body": "b"})
    assert response.status_code == 201
```

### Async tests

`asyncio_mode = "auto"` is set in `pyproject.toml`, so `async def test_*` works directly.

```python
async def test_async_list_notes() -> None:
    repo = InMemoryNoteRepository()
    result = await AsyncListNotesUseCase(repo).execute(ListNotesInput(limit=10, offset=0))
    assert result.total == 0
```

## In-memory SQLite for integration tests

When using `SqlAlchemyQueryExecutor` or `SqlAlchemyTransactionManager` with an in-memory SQLite database, always pass `poolclass=StaticPool`. Without it, SQLAlchemy may open a new physical connection that sees an empty database.

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

`StaticPool` guarantees all logical connections share the same underlying SQLite connection, so tables created in one operation are visible to the next.

**SQLite foreign-key enforcement**: SQLite disables foreign-key constraints by default. Enable them with `PRAGMA foreign_keys=ON` right after the engine is created:

```python
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("PRAGMA foreign_keys=ON"))
```

With `StaticPool`, one call applies to the single shared connection, so all subsequent operations see FK constraints enforced.

## Capturing structlog output with caplog

Call `configure_for_testing()` at module level in `conftest.py` to route structlog through stdlib logging so pytest's `caplog` fixture can capture it.

```python
# conftest.py
from nene2.log import configure_for_testing
configure_for_testing()
```

Then assert on message strings in tests:

```python
def test_handler_logs(caplog: pytest.LogCaptureFixture) -> None:
    client = TestClient(create_app())
    client.post("/api/echo", json={"message": "hello"})
    assert any("processing echo" in r.message for r in caplog.records)
```

**Note**: `caplog.records` returns stdlib `LogRecord` objects. Fields bound with `structlog.contextvars.bind_contextvars()` (such as `request_id`) are not directly accessible as `record.request_id` — they appear as part of the formatted message string instead.

## TestClient HTTP メソッドと json パラメーター

`TestClient` の `.get()`, `.post()`, `.put()`, `.patch()` は `json=` パラメーターを受け付けるが、
`.delete()` は受け付けない（`TypeError`）。DELETE にボディを付ける場合は `.request()` を使う。

```python
# ✅ GET/POST/PUT/PATCH は json= が使える
r = client.post("/items", json={"name": "Alice"})
r = client.put("/items/1", json={"name": "Bob"})

# ❌ DELETE は json= が使えない
r = client.delete("/items/bulk", json={"ids": [1, 2]})  # TypeError

# ✅ DELETE + ボディは request() を使う
r = client.request("DELETE", "/items/bulk", json={"ids": [1, 2]})
```

**設計上の注意**: DELETE にリクエストボディを持たせることは RFC 9110 では「推奨されない」（サーバーによっては無視される）。一括削除の代替として `POST /items/bulk-delete` パターンも検討する。

---

## Coverage requirements

| Scope | Target |
|---|---|
| Overall | ≥ 80% (CI enforced) |
| UseCase / Domain | ≥ 90% (goal) |

## Static analysis

```bash
uv run mypy src/          # Type checking (strict)
uv run ruff check src/    # Lint
uv run ruff format --check src/ tests/  # Format check
uv run pip-audit          # Dependency vulnerability scan
```
