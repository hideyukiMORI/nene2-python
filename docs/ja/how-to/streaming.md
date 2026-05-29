# How-to: ストリーミングレスポンス

`StreamingResponse` を使った SSE・NDJSON・CSV のストリーミングパターンを説明する。

---

## 1. Server-Sent Events (SSE)

リアルタイム通知や進捗更新に使う。

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
            "X-Accel-Buffering": "no",  # nginx プロキシのバッファリングを無効化
        },
    )
```

SSE フォーマット: 各メッセージは `data: ...\n\n`（改行2つ）で終わる。

---

## 2. NDJSON (Newline Delimited JSON)

大量データのストリーミング転送に使う。

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

## 3. CSV ストリーミング

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

## 4. `response_model` は使えない

`StreamingResponse` は `response_model` パラメーターと互換がない。OpenAPI スキーマに含まれるが、バリデーションは行われない。

```python
# ❌ StreamingResponse に response_model は指定しない
@app.get("/stream", response_model=SomeModel)
def stream() -> StreamingResponse: ...

# ✅ response_model は省略
@app.get("/stream")
def stream() -> StreamingResponse: ...
```

---

## 5. ミドルウェアとの共存

nene2 の `RequestIdMiddleware`・`SecurityHeadersMiddleware` は `StreamingResponse` にも適用される。ストリーミング中でもレスポンスヘッダーに `X-Request-Id` が付く。

---

## 6. テスト

`client.stream()` コンテキスト内では `r.text` / `r.content` は使えない（`ResponseNotRead`）。
`r.iter_lines()` / `r.iter_text()` / `r.iter_bytes()` でチャンクを収集する。

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
            # ✅ iter_text() でテキストを収集
            content = "".join(r.iter_text())
            # ❌ r.text は ResponseNotRead になる
        lines = [l for l in content.splitlines() if l]
        assert lines[0] == "id,name,email"
```
