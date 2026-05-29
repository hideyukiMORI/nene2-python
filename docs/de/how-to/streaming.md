# How-to: Streaming-Antworten

Streaming-Muster für SSE, NDJSON und CSV mit `StreamingResponse`.

---

## 1. Server-Sent Events (SSE)

Wird für Echtzeit-Benachrichtigungen und Fortschrittsaktualisierungen verwendet.

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
            "X-Accel-Buffering": "no",  # nginx-Proxy-Pufferung deaktivieren
        },
    )
```

SSE-Format: Jede Nachricht endet mit `data: ...\n\n` (zwei Zeilenumbrüche).

---

## 2. NDJSON (Newline Delimited JSON)

Wird für das Streaming großer Datenmengen verwendet.

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

## 3. CSV-Streaming

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

## 4. `response_model` kann nicht verwendet werden

`StreamingResponse` ist inkompatibel mit dem `response_model`-Parameter. Es würde im OpenAPI-Schema erscheinen, aber keine Validierung wird durchgeführt.

```python
# ❌ response_model nicht bei StreamingResponse angeben
@app.get("/stream", response_model=SomeModel)
def stream() -> StreamingResponse: ...

# ✅ response_model weglassen
@app.get("/stream")
def stream() -> StreamingResponse: ...
```

---

## 5. Koexistenz mit Middleware

nene2s `RequestIdMiddleware` und `SecurityHeadersMiddleware` gelten auch für eine `StreamingResponse`. Auch während des Streamings erhalten die Antwort-Header eine `X-Request-Id`.

---

## 6. Tests

Innerhalb eines `client.stream()`-Kontexts können `r.text` / `r.content` nicht verwendet werden (`ResponseNotRead`). Sammeln Sie Chunks mit `r.iter_lines()` / `r.iter_text()` / `r.iter_bytes()`.

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
            # ✅ Text mit iter_text() sammeln
            content = "".join(r.iter_text())
            # ❌ r.text würde ResponseNotRead auslösen
        lines = [l for l in content.splitlines() if l]
        assert lines[0] == "id,name,email"
```
