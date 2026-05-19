# Architecture overview

## Layer structure

nene2-python follows Clean Architecture. Dependencies flow from the outside in.

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

## Layer responsibilities

### HTTP Handler

- **Single responsibility**: parse the request, call a UseCase, return a response
- Uses Pydantic `BaseModel` for request body validation (HTTP boundary only)
- Contains zero domain logic
- Exposed via a `make_xxx_router()` factory function

```python
@router.post("", status_code=201)
async def create_note(body: CreateNoteBody) -> JSONResponse:
    note = create_use_case.execute(CreateNoteInput(title=body.title, body=body.body))
    return JSONResponse({"id": note.id, "title": note.title, "body": note.body}, status_code=201)
```

### UseCase

- **Single responsibility**: implement one business rule
- One method: `execute(input_: XxxInput) -> XxxOutput`
- No `import fastapi`, no `import sqlalchemy`
- Does not call other UseCases
- Testable with `InMemoryRepository` alone

### RepositoryInterface

- Defined as an ABC — the UseCase depends only on the interface
- Same interface is implemented by InMemory and SQLAlchemy versions
- `find_all`, `find_by_id`, `save`, `update`, `delete`, `count`

### ConcreteRepository

- SQLAlchemy Core (no ORM) with parameterised queries
- Queries are executed via `SqlAlchemyQueryExecutor`
- Table schema is managed centrally in `src/example/schema.py`

## Middleware stack

Requests pass through each middleware from outermost to innermost:

```
BearerTokenMiddleware        Authentication (Bearer Token)
ApiKeyAuthMiddleware         Authentication (API Key)
CORSMiddleware               CORS
ThrottleMiddleware           Rate limiting (fixed window)
RequestSizeLimitMiddleware   Payload size enforcement
RequestLoggingMiddleware     Structured request logging (structlog)
RequestIdMiddleware          X-Request-ID generation / propagation
SecurityHeadersMiddleware    Security response headers
ErrorHandlerMiddleware       Exceptions → RFC 9457 Problem Details
```

## Dependency injection

FastAPI's `Depends` is used at the HTTP boundary only. UseCases and repositories are wired via constructor injection in `app.py`.

```python
# app.py — wiring
note_repo = SqlAlchemyNoteRepository(executor)
app.include_router(make_note_router(
    list_use_case=ListNotesUseCase(note_repo),
    create_use_case=CreateNoteUseCase(note_repo),
    ...
))
```

## Domain package layout

```
src/example/<domain>/
  __init__.py
  entity.py              — @dataclass(frozen=True, slots=True)
  repository.py          — ABC + InMemory implementation
  exceptions.py          — XxxNotFoundException + ExceptionHandler
  use_case.py            — 5 UseCases + Input/Output DTOs
  handler.py             — FastAPI router factory
  sqlalchemy_repository.py — SQL backend
```
