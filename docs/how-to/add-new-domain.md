# Add a new domain

A checklist for adding a new domain following the same pattern as Note, Tag, and Comment.

## Checklist

### 1. Create the domain package

```bash
mkdir -p src/example/<domain>
touch src/example/<domain>/__init__.py
```

### 2. Create each file

| File | Content |
|---|---|
| `entity.py` | Entity as `@dataclass(frozen=True, slots=True)` |
| `repository.py` | `XxxRepositoryInterface(ABC)` + `InMemoryXxxRepository` |
| `exceptions.py` | `XxxNotFoundException` + `XxxNotFoundExceptionHandler` |
| `use_case.py` | 5 UseCases (List / Get / Create / Update / Delete) + Input/Output DTOs |
| `handler.py` | `make_xxx_router()` — parse → use-case → response |
| `sqlalchemy_repository.py` | SQL backend implementation |

### 3. Add the table to schema.py

Add a `CREATE TABLE` call to `ensure_schema()` in `src/example/schema.py`.

```python
executor.write(
    "CREATE TABLE IF NOT EXISTS your_domain ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "name TEXT NOT NULL,"
    "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
    ")"
)
```

### 4. Wire into app.py

Update `_build_repositories()` and `create_app()` in `src/example/app.py`.

```python
# Add to _build_repositories() return tuple
your_repo = SqlAlchemyYourRepository(executor)

# Register the router in create_app()
app.include_router(make_your_router(
    list_use_case=ListYourUseCase(your_repo),
    ...
))
```

### 5. Write tests

```
tests/example/<domain>/
  __init__.py
  test_<domain>_use_case.py     # UseCase unit tests (no DB)
  test_<domain>_repository.py   # Repository contract tests (InMemory + SQLAlchemy)
  test_<domain>_http.py         # HTTP integration tests (TestClient)
```

### 6. Register MCP tools (optional)

Add UseCase registrations to `create_mcp_server()` in `src/example/mcp.py`.

### 7. Pass all checks

```bash
uv run pytest && \
uv run mypy src/ && \
uv run ruff check src/ tests/ && \
uv run ruff format --check src/ tests/
```

## Naming conventions

| Target | Convention | Example |
|---|---|---|
| Entity class | PascalCase | `Note`, `Tag`, `Comment` |
| UseCase input DTO | `XxxInput` | `CreateNoteInput` |
| Exception | `XxxNotFoundException` | `NoteNotFoundException` |
| Handler factory | `make_xxx_router()` | `make_note_router()` |

## Reference implementations

- `src/example/note/` — basic CRUD domain
- `src/example/comment/` — nested domain with foreign key (`note_id`)
