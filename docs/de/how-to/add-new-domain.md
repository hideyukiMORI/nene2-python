# Neue Domain hinzufügen

Eine Checkliste für das Hinzufügen einer neuen Domain nach demselben Muster wie Note, Tag und Comment.

## Checkliste

### 1. Domain-Paket erstellen

```bash
mkdir -p src/example/<domain>
touch src/example/<domain>/__init__.py
```

### 2. Jede Datei erstellen

| Datei | Inhalt |
|---|---|
| `entity.py` | Entity als `@dataclass(frozen=True, slots=True)` |
| `repository.py` | `XxxRepositoryInterface(ABC)` + `InMemoryXxxRepository` |
| `exceptions.py` | `XxxNotFoundException` + `XxxNotFoundExceptionHandler` |
| `use_case.py` | 5 UseCases (List / Get / Create / Update / Delete) + Input/Output-DTOs |
| `handler.py` | `make_xxx_router()` — parse → use-case → response |
| `sqlalchemy_repository.py` | SQL-Backend-Implementierung |

### 3. Tabelle zu schema.py hinzufügen

Fügen Sie einen `CREATE TABLE`-Aufruf zu `ensure_schema()` in `src/example/schema.py` hinzu.

```python
executor.write(
    "CREATE TABLE IF NOT EXISTS your_domain ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "name TEXT NOT NULL,"
    "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
    ")"
)
```

### 4. In app.py einbinden

Aktualisieren Sie `_build_repositories()` und `create_app()` in `src/example/app.py`.

```python
# Zum Rückgabe-Tupel von _build_repositories() hinzufügen
your_repo = SqlAlchemyYourRepository(executor)

# Router in create_app() registrieren
app.include_router(make_your_router(
    list_use_case=ListYourUseCase(your_repo),
    ...
))
```

### 5. Tests schreiben

```
tests/example/<domain>/
  __init__.py
  test_<domain>_use_case.py     # UseCase-Unit-Tests (ohne DB)
  test_<domain>_repository.py   # Repository-Contract-Tests (InMemory + SQLAlchemy)
  test_<domain>_http.py         # HTTP-Integrationstests (TestClient)
```

### 6. MCP-Tools registrieren (optional)

Fügen Sie UseCase-Registrierungen zu `create_mcp_server()` in `src/example/mcp.py` hinzu.

### 7. Alle Prüfungen bestehen

```bash
uv run pytest && \
uv run mypy src/ && \
uv run ruff check src/ tests/ && \
uv run ruff format --check src/ tests/
```

## Namenskonventionen

| Ziel | Konvention | Beispiel |
|---|---|---|
| Entity-Klasse | PascalCase | `Note`, `Tag`, `Comment` |
| UseCase-Input-DTO | `XxxInput` | `CreateNoteInput` |
| Ausnahme | `XxxNotFoundException` | `NoteNotFoundException` |
| Handler-Factory | `make_xxx_router()` | `make_note_router()` |

## Referenzimplementierungen

- `src/example/note/` — einfache CRUD-Domain
- `src/example/comment/` — verschachtelte Domain mit Fremdschlüssel (`note_id`)
