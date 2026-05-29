# How-to: choosing a concurrency pattern

A guide consolidating the findings of FT188 (threading) through FT192 (asyncio).
In nene2-python the **UseCase layer is HTTP-independent**, so the choice of
concurrency is made in the UseCase or the HTTP handler layer.

---

## Quick selection table

| Use case | Recommended | FT |
|---|---|---|
| Waiting on I/O inside a FastAPI handler | `async def` + `await` | FT192 |
| Run a sync UseCase non-blockingly | `AsyncUseCaseProtocol` | FT6, FT14 |
| Offload CPU-bound work to a thread | `asyncio.to_thread()` or `ThreadPoolExecutor` | FT188, FT191 |
| Offload CPU-bound work to a process | `ProcessPoolExecutor` / `multiprocessing` | FT190, FT191 |
| External command in the background | `subprocess` (`shell=False` + allowlist) | FT189 |
| Shared in-memory cache | `TtlCache[V]` (thread-safe) | FT119, FT171 |

---

## asyncio (FT192)

FastAPI routes are `async def` by default. To parallelize multiple I/O operations:

```python
import asyncio

async def execute(self, input_: ListNotesInput) -> ListNotesOutput:
    items_task = asyncio.create_task(self._repository.find_all_async(...))
    total_task = asyncio.create_task(self._repository.count_async())
    items, total = await asyncio.gather(items_task, total_task)
    return ListNotesOutput(items=items, total=total, ...)
```

**Note**: Pydantic v2 truncates `float` to `int`. Make numeric bounds explicit with
`Field(ge=..., le=...)`.

---

## threading (FT188)

Under the GIL this is unsuited to CPU parallelism, but it is useful as a bridge to
**legacy APIs whose blocking I/O hasn't been made async**.

- `threading.Lock` / `asyncio.Lock` — protect shared state
- `ThreadPoolExecutor` — offload sync functions (combine with FT191)

---

## subprocess (FT189)

**Mandatory rules** (CLAUDE.md / FT189 security diagnosis):

1. `shell=False` only
2. Validate the command name against an allowlist
3. Set a timeout and an stdout size limit
4. `# noqa: S603` for ruff only after the allowlist check (state the reason in the docstring)

---

## Alignment with nene2

| Layer | Concurrency |
|---|---|
| UseCase | `AsyncUseCaseProtocol` or pure-sync (InMemory testable) |
| HTTP | `async def` handlers, `BackgroundTasks` ([background-tasks.md](background-tasks.md)) |
| Middleware | sync ASGI; don't put blocking work inside middleware |
| MCP | expose the UseCase as a tool directly — concurrency stays inside the UseCase |

Detailed reports: [FT188](../field-trials/2026-05-field-trial-188.md) · [FT189](../field-trials/2026-05-field-trial-189.md) · [FT190](../field-trials/2026-05-field-trial-190.md) · [FT191](../field-trials/2026-05-field-trial-191.md) · [FT192](../field-trials/2026-05-field-trial-192.md)
