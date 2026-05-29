# One UseCase, two surfaces (HTTP + MCP)

The headline NENE2 promise is **"LLM delivery ready"**: the same domain logic is
delivered both as a JSON HTTP API for applications *and* as
[MCP](https://modelcontextprotocol.io/) tools for LLM agents — written once, with
no per-surface duplication. This page shows exactly how, in the reference app.

## The shared core

Domain logic lives in **UseCase** classes that know nothing about FastAPI or
SQLAlchemy ([`src/example/note/use_case.py`](../../src/example/note/use_case.py)).
Both surfaces construct the *same* UseCase and call `.execute()`:

**HTTP** — [`src/example/note/handler.py`](../../src/example/note/handler.py):

```python
@router.post("", status_code=201, response_model=NoteResponse, summary="Create a note")
async def create_note(body: CreateNoteBody) -> NoteResponse:
    note = create_use_case.execute(CreateNoteInput(body.title, body.body))
    return NoteResponse(id=note.id, title=note.title, body=note.body)
```

The handler is pure *parse → use-case → response*: it carries no domain rules. The
length and non-empty checks live in `CreateNoteInput` (below), so they hold no
matter which surface called.

**MCP** — [`src/example/mcp.py`](../../src/example/mcp.py):

```python
@server.tool("Create a new note.")
def create_note(title: str, body: str) -> dict:
    return asdict(note_create.execute(CreateNoteInput(title=title, body=body)))
```

Same `CreateNoteUseCase`, same `CreateNoteInput`, same repository — only the
**edge** differs. The UseCase `Input`/`Output` DTOs *are* the contract for both
surfaces; FastMCP derives the tool schema from the function signature, FastAPI
derives the OpenAPI schema from the Pydantic body and `response_model`.

## What this buys you

- Write and test the domain **once**; deliver it to apps (HTTP) and to agents
  (MCP) from the same code path.
- A bug fixed in the UseCase is fixed on **both** surfaces simultaneously.
- New domains are reachable by agents the moment their UseCases exist — `mcp.py`
  wires 15 tools (Note / Tag / Comment) with no extra plumbing.

## Proof (a test, not a claim)

[`tests/example/test_http_mcp_parity.py`](../../tests/example/test_http_mcp_parity.py)
wires an HTTP app and an MCP server onto the **same** SQLite store and asserts the
surfaces are interchangeable:

- a note created through the MCP `create_note` tool is readable through `GET /examples/notes/{id}`,
- a note created through HTTP `POST /examples/notes` is readable through the MCP `get_note` tool,
- both writes land in one store.

This guards the differentiator as a regression test — if the two surfaces ever
drift apart, CI fails.

## What is shared, and what is not

The dividing line is **domain rule vs. transport mechanic**. Anything that must be
true of a note regardless of how it arrived lives in the UseCase Input DTO and is
therefore enforced on both surfaces; protocol plumbing stays at the edge.

| Concern | Where it lives | Shared with MCP? |
|---|---|---|
| Length limits (`max_length`), non-empty | `CreateNoteInput.__post_init__` in `use_case.py` | **Yes** |
| Create / read / update / delete logic, not-found semantics | UseCase + entity | **Yes** |
| Request parsing, argument shape/types | Pydantic body (HTTP) / FastMCP signature (MCP) | Each surface's own |
| Authentication, CORS, throttling | middleware in `app.py` | No |
| Pagination parsing, RFC 9457 error formatting | HTTP layer | No |

The HTTP `CreateNoteBody` mirrors `max_length` via the same
`MAX_NOTE_TITLE_LENGTH` constant — so the limit is declared once, documented in
OpenAPI, *and* enforced in the domain for the MCP path.

This is the **API-first / thin-HTTP-layer** principle in action: the edge adapts
each protocol, the center holds the domain. The practical rule for implementers:

> If a rule must hold for **both** surfaces, put it in the UseCase or the entity —
> not in the handler. A check that lives only in the HTTP handler does **not**
> protect the MCP tool. (This is exactly why the length and non-empty checks were
> moved into the Input DTOs — see the parity tests.)

## See also

- [Design philosophy → LLM Delivery Ready](design-philosophy.md)
- [Architecture overview](architecture.md)
- [ADR 0011 — MCP as a core dependency](../adr/0011-mcp-as-core-dependency.md)
- [How to set up the MCP server](../howto/mcp-setup.md)
