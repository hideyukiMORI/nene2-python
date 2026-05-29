# Guide pratique : réponses en streaming

Schémas de streaming pour SSE, NDJSON et CSV avec `StreamingResponse`.

---

## 1. Server-Sent Events (SSE)

Utilisé pour les notifications en temps réel et les mises à jour de progression.

```python
import asyncio
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

async def sse_generator(topic: str) -> AsyncIterator[str]:
    for i in range(5):
        yield f"data: {{'topic': '{topic}', 'count': {i}}}\n\n"
        await asyncio.sleep(1)
    yield "data: {\"done\": true}\n\n"

@app.get("/events/{topic}")
async def stream_events(topic: str) -> StreamingResponse:
    return StreamingResponse(
        sse_generator(topic),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # désactiver le buffering du proxy nginx
        },
    )
```

Format SSE : chaque message se termine par `data: ...\n\n` (deux sauts de ligne).

---

## 2. NDJSON (Newline Delimited JSON)

Utilisé pour diffuser de grandes quantités de données.

```python
import json
from collections.abc import AsyncIterator

async def ndjson_generator(items: list[dict[str, object]]) -> AsyncIterator[str]:
    for item in items:
        yield json.dumps(item, ensure_ascii=False) + "\n"

@app.get("/export/items")
async def export_items() -> StreamingResponse:
    items = fetch_all_items()
    return StreamingResponse(
        ndjson_generator(items),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=items.ndjson"},
    )
```

---

## 3. Streaming CSV

```python
import csv
import io
from collections.abc import Iterator

def csv_generator(rows: list[dict[str, object]]) -> Iterator[str]:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["id", "name", "email"])
    writer.writeheader()
    yield buf.getvalue()
    buf.seek(0)
    buf.truncate()

    for row in rows:
        writer.writerow(row)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate()

@app.get("/export/users.csv")
def export_users_csv() -> StreamingResponse:
    rows = fetch_all_users()
    return StreamingResponse(
        csv_generator(rows),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"},
    )
```

---

## 4. `response_model` ne peut pas être utilisé

`StreamingResponse` est incompatible avec le paramètre `response_model`. Il apparaîtrait dans
le schéma OpenAPI mais aucune validation ne serait effectuée.

```python
# ❌ ne pas spécifier response_model sur un StreamingResponse
@app.get("/stream", response_model=SomeModel)
def stream() -> StreamingResponse: ...

# ✅ omettre response_model
@app.get("/stream")
def stream() -> StreamingResponse: ...
```

---

## 5. Coexistence avec le middleware

Le `RequestIdMiddleware` et le `SecurityHeadersMiddleware` de nene2 s'appliquent aussi à une
`StreamingResponse`. Même pendant le streaming, les en-têtes de réponse reçoivent un
`X-Request-Id`.

---

## 6. Tests

Dans un contexte `client.stream()`, `r.text` / `r.content` ne peuvent pas être utilisés
(`ResponseNotRead`). Collectez les chunks avec `r.iter_lines()` / `r.iter_text()` / `r.iter_bytes()`.

```python
def test_sse_stream() -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        with client.stream("GET", "/events/test") as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
            lines = []
            for line in r.iter_lines():
                lines.append(line)
                if len(lines) >= 3:
                    break
            assert any("data:" in line for line in lines)

def test_csv_stream() -> None:
    with TestClient(app) as client:
        with client.stream("GET", "/export/users.csv") as r:
            assert r.status_code == 200
            # ✅ collecter le texte avec iter_text()
            content = "".join(r.iter_text())
            # ❌ r.text lèverait ResponseNotRead
        lines = [l for l in content.splitlines() if l]
        assert lines[0] == "id,name,email"
```
