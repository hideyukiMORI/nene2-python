# 操作指南：流式响应

使用 `StreamingResponse` 实现 SSE、NDJSON 和 CSV 流式传输的模式。

---

## 1. Server-Sent Events（SSE）

用于实时通知和进度更新。

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
            "X-Accel-Buffering": "no",  # 禁用 nginx 代理缓冲
        },
    )
```

SSE 格式：每条消息以 `data: ...\n\n`（两个换行符）结尾。

---

## 2. NDJSON（换行符分隔的 JSON）

用于流式传输大量数据。

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

## 3. CSV 流式传输

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

## 4. `response_model` 不可用

`StreamingResponse` 与 `response_model` 参数不兼容。该参数会出现在 OpenAPI schema 中，但不会执行任何验证。

```python
# ❌ 不要在 StreamingResponse 上指定 response_model
@app.get("/stream", response_model=SomeModel)
def stream() -> StreamingResponse: ...

# ✅ 省略 response_model
@app.get("/stream")
def stream() -> StreamingResponse: ...
```

---

## 5. 与 middleware 共存

nene2 的 `RequestIdMiddleware` 和 `SecurityHeadersMiddleware` 也适用于 `StreamingResponse`。即使在流式传输期间，响应头也会包含 `X-Request-Id`。

---

## 6. 测试

在 `client.stream()` 上下文中，不能使用 `r.text` / `r.content`（会引发 `ResponseNotRead`）。使用 `r.iter_lines()` / `r.iter_text()` / `r.iter_bytes()` 收集数据块。

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
            # ✅ 使用 iter_text() 收集文本
            content = "".join(r.iter_text())
            # ❌ r.text 会引发 ResponseNotRead
        lines = [l for l in content.splitlines() if l]
        assert lines[0] == "id,name,email"
```
