# Tests ausführen

## Grundlegende Befehle

```bash
# Alle Tests mit Coverage ausführen
uv run pytest

# Ausführliche Ausgabe bei Fehler
uv run pytest --tb=short -v

# Ein spezifisches Verzeichnis ausführen
uv run pytest tests/example/note/

# Einen HTML-Coverage-Bericht erstellen
uv run pytest --cov=src --cov-report=html
# → öffnen Sie htmlcov/index.html im Browser
```

## Teststruktur

```
tests/
  nene2/              Framework-Kern-Unit-Tests
    use_case/         UseCaseProtocol-Konformität
    auth/             Auth-Middleware und -Verifizierer
    database/         TransactionManager-Tests
    mcp/              McpHttpClient-Tests
    middleware/       Jede Middleware isoliert
  example/
    note/             Note-Domain-Tests
      test_list_notes.py           UseCase-Unit-Tests
      test_note_repository.py      Repository-Contract-Tests
      test_async_note_use_case.py  Async-UseCase-Tests
    comment/
      test_comment_use_case.py     UseCase-Unit-Tests (ohne DB)
      test_comment_repository.py   InMemory + SQLAlchemy-Contract-Tests
      test_comment_http.py         HTTP-Integrationstests (TestClient)
```

## Testtypen

### UseCase-Unit-Tests

Keine Datenbank, kein HTTP — verwenden InMemory-Repositories. Am schnellsten.

```python
def test_create_note() -> None:
    repo = InMemoryNoteRepository()
    note = CreateNoteUseCase(repo).execute(CreateNoteInput(title="t", body="b"))
    assert note.title == "t"
```

### Repository-Contract-Tests

`@pytest.fixture(params=["inmemory", "sqlalchemy"])` führt dieselben Assertions gegen beide Implementierungen aus.

```python
@pytest.fixture(params=["inmemory", "sqlalchemy"])
def repo(request): ...

def test_save_and_find(repo) -> None:
    note = repo.save("title", "body")
    assert repo.find_by_id(note.id) == note
```

### HTTP-Integrationstests

Verwenden FastAPIs `TestClient`. Testet den vollständigen Stack von HTTP bis Repository.

```python
def test_create_note_returns_201() -> None:
    client = TestClient(create_app(AppSettings(throttle_enabled=False)))
    response = client.post("/notes", json={"title": "t", "body": "b"})
    assert response.status_code == 201
```

### Async-Tests

`asyncio_mode = "auto"` ist in `pyproject.toml` gesetzt, sodass `async def test_*` direkt funktioniert.

```python
async def test_async_list_notes() -> None:
    repo = InMemoryNoteRepository()
    result = await AsyncListNotesUseCase(repo).execute(ListNotesInput(limit=10, offset=0))
    assert result.total == 0
```

## In-Memory-SQLite für Integrationstests

Bei Verwendung von `SqlAlchemyQueryExecutor` oder `SqlAlchemyTransactionManager` mit einer In-Memory-SQLite-Datenbank übergeben Sie immer `poolclass=StaticPool`. Ohne diese öffnet SQLAlchemy möglicherweise eine neue physische Verbindung, die eine leere Datenbank sieht.

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

`StaticPool` garantiert, dass alle logischen Verbindungen dieselbe zugrunde liegende SQLite-Verbindung teilen, sodass in einer Operation erstellte Tabellen in der nächsten sichtbar sind.

**SQLite-Fremdschlüssel-Durchsetzung**: SQLite deaktiviert Fremdschlüssel-Constraints standardmäßig. Aktivieren Sie sie mit `PRAGMA foreign_keys=ON` direkt nach dem Erstellen des Motors:

```python
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("PRAGMA foreign_keys=ON"))
```

Mit `StaticPool` gilt ein Aufruf für die einzelne gemeinsame Verbindung, sodass alle nachfolgenden Operationen FK-Constraints durchgesetzt sehen.

## structlog-Ausgabe mit caplog erfassen

Rufen Sie `configure_for_testing()` auf Modulebene in `conftest.py` auf, um structlog durch stdlib-Logging zu leiten, damit das pytest-`caplog`-Fixture es erfassen kann.

```python
# conftest.py
from nene2.log import configure_for_testing
configure_for_testing()
```

Dann Assertions auf Nachrichtenstrings in Tests:

```python
def test_handler_logs(caplog: pytest.LogCaptureFixture) -> None:
    client = TestClient(create_app())
    client.post("/api/echo", json={"message": "hello"})
    assert any("processing echo" in r.message for r in caplog.records)
```

**Hinweis**: `caplog.records` gibt stdlib-`LogRecord`-Objekte zurück. Mit `structlog.contextvars.bind_contextvars()` gebundene Felder (wie `request_id`) sind nicht direkt als `record.request_id` zugänglich — sie erscheinen stattdessen als Teil des formatierten Nachrichtenstrings.

## TestClient-HTTP-Methoden und der json-Parameter

`TestClient`s `.get()`, `.post()`, `.put()`, `.patch()` akzeptieren den `json=`-Parameter, aber `.delete()` tut es nicht (`TypeError`). Wenn Sie DELETE mit einem Body senden müssen, verwenden Sie `.request()`.

```python
# ✅ GET/POST/PUT/PATCH können json= verwenden
r = client.post("/items", json={"name": "Alice"})
r = client.put("/items/1", json={"name": "Bob"})

# ❌ DELETE kann json= nicht verwenden
r = client.delete("/items/bulk", json={"ids": [1, 2]})  # TypeError

# ✅ DELETE + Body: request() verwenden
r = client.request("DELETE", "/items/bulk", json={"ids": [1, 2]})
```

**Designhinweis**: Das Übergeben eines Request-Bodys an DELETE ist gemäß RFC 9110 "nicht empfohlen" (einige Server ignorieren es). Als Alternative zur Massenlöschung erwägen Sie auch das Muster `POST /items/bulk-delete`.

---

## Coverage-Anforderungen

| Bereich | Ziel |
|---|---|
| Gesamt | ≥ 80% (CI erzwungen via `pytest --cov-fail-under=80`) |
| UseCase / Domain | ≥ 90% (CI erzwungen für `example/*/use_case.py`, `entity.py`, `async_use_case.py`) |

Aktuelle Basis: **466 Tests**, ~93% Gesamtcoverage.

## Statische Analyse

```bash
uv run mypy src/          # Typprüfung (streng)
uv run ruff check src/ tests/    # Lint
uv run ruff format --check src/ tests/  # Formatprüfung
uv run pip-audit --ignore-vuln PYSEC-2025-183  # Abhängigkeitsscan (entspricht CI)
```

CI läuft auf **Python 3.12 und 3.14** (siehe `.github/workflows/ci.yml`).
