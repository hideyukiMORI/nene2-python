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
