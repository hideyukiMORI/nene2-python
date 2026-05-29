# How-to: response patterns

Patterns for returning responses with FastAPI + nene2.

**The default is "return an instance of the response model"** (§1). You return a
`JSONResponse` by hand only in special cases — custom status / headers /
streaming / mixing success and error (§3 onward). The reference implementation
`src/example/*/handler.py` is uniformly the former.

---

## 1. Default pattern: return a response-model instance

The handler declares `response_model` and **returns an instance of that type**.
FastAPI validates the content and serializes it exactly as the declared schema
(so OpenAPI and the response body match).

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class NoteResponse(BaseModel):
    note_id: int = Field(description="Note ID")
    title: str = Field(description="Title")


# ✅ default: return the model instance → FastAPI validates + serializes
@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int) -> NoteResponse:
    return NoteResponse(note_id=note_id, title="Hello")
```

> ⚠️ Even with `response_model` set, **returning a `JSONResponse` directly skips
> validation of its content** (`response_model` is only used for OpenAPI schema
> generation; the body is sent as-is). For normal routes, return the model
> instance so validation applies. Use `JSONResponse` only for the special cases in
> §3 onward. CLAUDE.md also mandates "declare `response_model`; no `Any` returns."

---

## 2. Domain dataclass vs. Pydantic response model: two definitions

In nene2 the domain layer and HTTP layer are separated, so two classes with the
same fields appear.

```python
# Domain layer: frozen dataclass (DB return values, UseCase I/O)
@dataclass(frozen=True, slots=True)
class Note:
    note_id: int
    title: str

# HTTP layer: Pydantic model (OpenAPI schema generation, validation)
class NoteResponse(BaseModel):
    note_id: int = Field(description="Note ID")
    title: str = Field(description="Title")
```

**Why two?** A `dataclass` is a value object expressing domain invariants; a
`Pydantic BaseModel` is the HTTP-boundary serialization/schema definition. They
have different responsibilities.

Convert explicitly in the handler and **return the model instance** (the default
pattern from §1):

```python
@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int) -> NoteResponse:
    note = get_use_case.execute(GetNoteInput(note_id))
    return NoteResponse(note_id=note.note_id, title=note.title)
```

---

## 3. Mixing problem_details_response() and JSONResponse

When the same endpoint returns a `JSONResponse` on success and a
`problem_details_response()` on error, the return types differ. Both are instances
or subclasses of `JSONResponse`, so the return type can be unified as
`JSONResponse`.

```python
@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int) -> JSONResponse:
    if note_id not in _notes:
        return problem_details_response("not-found", "Not Found", 404, "Note not found.")
    return JSONResponse({"note_id": note_id, "title": "Hello"})
```

---

## 4. The `response: Response` parameter is incompatible with JSONResponse

Adding headers via FastAPI's `response: Response` parameter and returning a
`JSONResponse` directly **cannot be mixed**.

```python
# ❌ headers set via response: Response are not reflected in a JSONResponse
@app.get("/items/{item_id}")
def get_item(item_id: int, response: Response) -> JSONResponse:
    response.headers["X-Custom"] = "value"  # has no effect
    return JSONResponse({"item_id": item_id})

# ✅ pass headers directly to JSONResponse
@app.get("/items/{item_id}")
def get_item(item_id: int) -> JSONResponse:
    return JSONResponse({"item_id": item_id}, headers={"X-Custom": "value"})
```

The `response: Response` parameter only works when FastAPI auto-generates the
response object (i.e. when you return a `dict`).

---

## 5. Pass `mode="json"` when handing model_dump() to JSONResponse

When you pass `model_dump()` directly to `JSONResponse`, Python objects such as
`datetime` cannot be serialized by `json.dumps` and you get a 500. Specifying
`mode="json"` makes Pydantic convert to JSON-compatible types.

```python
from pydantic import BaseModel
from datetime import datetime

class OrderLine(BaseModel):
    created_at: datetime
    quantity: int

line = OrderLine(created_at=datetime(2026, 1, 1), quantity=3)

# ❌ TypeError: Object of type datetime is not JSON serializable
return JSONResponse(line.model_dump())

# ✅ mode="json" converts datetime → ISO 8601 string
return JSONResponse(line.model_dump(mode="json"))
```

**When this bites**: normal routes using `response_model=` are fine because
FastAPI converts automatically. Watch out on routes that return `JSONResponse`
directly (207 Multi-Status, custom responses, a `/preview` containing nested
models, etc.).

---

## 6. 204 No Content and response_model

Specifying `response_model` on a `204 No Content` endpoint causes a FastAPI
assertion error.

```python
# ❌ response_model can't be specified with 204
@app.delete("/notes/{note_id}", status_code=204, response_model=SomeModel)
def delete_note(note_id: int) -> None: ...

# ✅ omit response_model
@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int) -> None: ...
```
