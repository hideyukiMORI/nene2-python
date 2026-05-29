# Architekturübersicht

## Schichtenstruktur

nene2-python folgt der Clean Architecture. Abhängigkeiten fließen von außen nach innen.

```
┌─────────────────────────────────────────────┐
│  HTTP Handler (FastAPI router)              │
│  parse request → call use-case → response  │
├─────────────────────────────────────────────┤
│  UseCase                                    │
│  Business logic — no HTTP or DB knowledge  │
├─────────────────────────────────────────────┤
│  RepositoryInterface (ABC)                  │
│  Contract for the operations the domain     │
│  needs                                      │
├─────────────────────────────────────────────┤
│  ConcreteRepository                         │
│  SQLAlchemy / InMemory implementations      │
└─────────────────────────────────────────────┘
```

## Verantwortlichkeiten der Schichten

### HTTP-Handler

- **Einzelne Verantwortung**: Anfrage parsen, einen UseCase aufrufen, eine Antwort zurückgeben
- Verwendet Pydantic `BaseModel` zur Validierung des Anfrage-Bodys (nur an der HTTP-Grenze)
- Enthält keine Domänenlogik
- Wird über eine `make_xxx_router()`-Factory-Funktion bereitgestellt

```python
@router.post("", status_code=201)
async def create_note(body: CreateNoteBody) -> JSONResponse:
    note = create_use_case.execute(CreateNoteInput(title=body.title, body=body.body))
    return JSONResponse({"id": note.id, "title": note.title, "body": note.body}, status_code=201)
```

### UseCase

- **Einzelne Verantwortung**: eine Geschäftsregel implementieren
- Eine Methode: `execute(input_: XxxInput) -> XxxOutput`
- Kein `import fastapi`, kein `import sqlalchemy`
- Ruft keine anderen UseCases auf
- Mit `InMemoryRepository` allein testbar

### RepositoryInterface

- Definiert als ABC — der UseCase hängt nur vom Interface ab
- Dasselbe Interface wird von InMemory- und SQLAlchemy-Versionen implementiert
- `find_all`, `find_by_id`, `save`, `update`, `delete`, `count`

### ConcreteRepository

- SQLAlchemy Core (kein ORM) mit parametrisierten Abfragen
- Abfragen werden über `SqlAlchemyQueryExecutor` ausgeführt
- Tabellenschema: Die Beispielanwendung verwendet eine zentrale `src/example/schema.py`; für neue Projekte definieren Sie `ensure_schema()` in der `sqlalchemy_repository.py` jeder Domain und rufen sie alle aus `create_app()` auf

## Middleware-Stack

Anfragen durchlaufen jede Middleware von außen nach innen:

```
BearerTokenMiddleware        Authentifizierung (Bearer Token)
ApiKeyAuthMiddleware         Authentifizierung (API Key)
CORSMiddleware               CORS
ThrottleMiddleware           Rate-Limiting (Festfenster)
RequestSizeLimitMiddleware   Payload-Größenbeschränkung
RequestLoggingMiddleware     Strukturiertes Anfrage-Logging (structlog)
RequestIdMiddleware          X-Request-ID-Generierung / -Weitergabe
SecurityHeadersMiddleware    Sicherheits-Response-Header
ErrorHandlerMiddleware       Ausnahmen → RFC 9457 Problem Details
```

## Dependency Injection

FastAPIs `Depends` wird nur an der HTTP-Grenze verwendet. UseCases und Repositories werden über Constructor Injection in `app.py` verdrahtet.

```python
# app.py — Verdrahtung
note_repo = SqlAlchemyNoteRepository(executor)
app.include_router(make_note_router(
    list_use_case=ListNotesUseCase(note_repo),
    create_use_case=CreateNoteUseCase(note_repo),
    ...
))
```

## Domain-Paketstruktur

```
src/example/<domain>/
  __init__.py
  entity.py              — @dataclass(frozen=True, slots=True)
  repository.py          — ABC + InMemory-Implementierung
  exceptions.py          — XxxNotFoundException + ExceptionHandler
  use_case.py            — 5 UseCases + Input/Output-DTOs
  handler.py             — FastAPI-Router-Factory
  sqlalchemy_repository.py — SQL-Backend
```
