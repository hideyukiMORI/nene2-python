# How-to: Nebenläufigkeitsmuster auswählen

Ein Leitfaden, der die Erkenntnisse von FT188 (Threading) bis FT192 (asyncio) zusammenfasst. In nene2-python ist die **UseCase-Schicht HTTP-unabhängig**, sodass die Wahl der Nebenläufigkeit im UseCase oder der HTTP-Handler-Schicht getroffen wird.

---

## Schnellauswahltabelle

| Anwendungsfall | Empfehlung | FT |
|---|---|---|
| Auf I/O innerhalb eines FastAPI-Handlers warten | `async def` + `await` | FT192 |
| Einen synchronen UseCase nicht-blockierend ausführen | `AsyncUseCaseProtocol` | FT6, FT14 |
| CPU-intensive Arbeit in einen Thread auslagern | `asyncio.to_thread()` oder `ThreadPoolExecutor` | FT188, FT191 |
| CPU-intensive Arbeit in einen Prozess auslagern | `ProcessPoolExecutor` / `multiprocessing` | FT190, FT191 |
| Externen Befehl im Hintergrund ausführen | `subprocess` (`shell=False` + Allowlist) | FT189 |
| Gemeinsamer In-Memory-Cache | `TtlCache[V]` (thread-sicher) | FT119, FT171 |

---

## asyncio (FT192)

FastAPI-Routen sind standardmäßig `async def`. Um mehrere I/O-Operationen zu parallelisieren:

```python
import asyncio

async def execute(self, input_: ListNotesInput) -> ListNotesOutput:
    items_task = asyncio.create_task(self._repository.find_all_async(...))
    total_task = asyncio.create_task(self._repository.count_async())
    items, total = await asyncio.gather(items_task, total_task)
    return ListNotesOutput(items=items, total=total, ...)
```

**Hinweis**: Pydantic v2 kürzt `float` auf `int`. Machen Sie numerische Grenzen explizit mit `Field(ge=..., le=...)`.

---

## threading (FT188)

Unter dem GIL ist dies für CPU-Parallelismus ungeeignet, aber nützlich als Brücke zu **Legacy-APIs, deren blockierende I/O noch nicht async gemacht wurde**.

- `threading.Lock` / `asyncio.Lock` — gemeinsamen Zustand schützen
- `ThreadPoolExecutor` — synchrone Funktionen auslagern (zusammen mit FT191 kombinieren)

---

## subprocess (FT189)

**Pflichtregeln** (CLAUDE.md / FT189-Sicherheitsdiagnose):

1. Ausschließlich `shell=False`
2. Befehlsnamen gegen eine Allowlist validieren
3. Timeout und stdout-Größenlimit setzen
4. `# noqa: S603` für ruff nur nach der Allowlist-Prüfung (Begründung im Docstring angeben)

---

## Ausrichtung an nene2

| Schicht | Nebenläufigkeit |
|---|---|
| UseCase | `AsyncUseCaseProtocol` oder rein synchron (InMemory-testbar) |
| HTTP | `async def`-Handler, `BackgroundTasks` ([background-tasks.md](background-tasks.md)) |
| Middleware | Synchrones ASGI; keine blockierende Arbeit innerhalb der Middleware |
| MCP | UseCase direkt als Tool bereitstellen — Nebenläufigkeit bleibt innerhalb des UseCase |

Detaillierte Berichte: [FT188](../field-trials/2026-05-field-trial-188.md) · [FT189](../field-trials/2026-05-field-trial-189.md) · [FT190](../field-trials/2026-05-field-trial-190.md) · [FT191](../field-trials/2026-05-field-trial-191.md) · [FT192](../field-trials/2026-05-field-trial-192.md)
