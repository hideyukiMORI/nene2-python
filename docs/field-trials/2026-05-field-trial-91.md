# FT91: ストリーミングレスポンス — StreamingResponse と SSE パターン検証

**日付**: 2026-05-20  
**テーマ**: StreamingResponse（テキスト・SSE・NDJSON・CSV）と nene2 ミドルウェアの共存  
**バージョン**: v1.8.30  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft91-streaming/`

---

## 概要

Starlette の `StreamingResponse` を使ったストリーミングパターン（テキスト・SSE・NDJSON・CSV）と
nene2 ミドルウェアの共存を検証。nene2 のミドルウェア（RequestId, SecurityHeaders 等）は
StreamingResponse とも問題なく共存した。
`response_model` が使えず OpenAPI スキーマが不完全になることと、
TestClient がストリーミングをバッファリングすることが摩擦として発見された。

---

## 4パターンの実装

### パターン1: シンプルテキストストリーミング

```python
@app.get("/stream/numbers")
def stream_numbers(count: int = 10) -> StreamingResponse:
    async def generate():
        for i in range(1, count + 1):
            yield f"{i}\n".encode()
    return StreamingResponse(generate(), media_type="text/plain")
```

### パターン2: Server-Sent Events (SSE)

```python
async def _generate_sse(events):
    for event in events:
        yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n".encode()

@app.get("/stream/events")
def stream_events() -> StreamingResponse:
    return StreamingResponse(
        _generate_sse(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### パターン3: JSON Lines (NDJSON)

```python
@app.get("/stream/json-lines")
def stream_json_lines(count: int = 5) -> StreamingResponse:
    async def generate():
        for i in range(1, count + 1):
            yield (json.dumps({"id": i, "value": i * 2}) + "\n").encode()
    return StreamingResponse(generate(), media_type="application/x-ndjson")
```

### パターン4: CSV ダウンロード

```python
@app.get("/stream/large-csv")
def stream_large_csv(rows: int = 100) -> StreamingResponse:
    async def generate():
        yield b"id,name,value\n"
        for i in range(1, min(rows, 10000) + 1):
            yield f"{i},item-{i},{i * 10}\n".encode()
    return StreamingResponse(
        generate(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=data.csv"},
    )
```

---

## 発見した問題

### 問題1: StreamingResponse で `response_model` が使えない

```python
# ❌ response_model に何を指定するか不明
@app.get("/stream", response_model=???)
def stream() -> StreamingResponse:
    ...

# ✅ 現状: response_model を省略 → OpenAPI スキーマに型情報なし
@app.get("/stream")
def stream() -> StreamingResponse:
    ...
```

nene2 の CLAUDE.md には「`response_model` で明示（`Any` 返却禁止）」とあるが、
`StreamingResponse` では対応するモデルがない。
OpenAPI スキーマで media_type と説明だけ出すことはできるが型情報は持てない。

### 問題2: TestClient がストリーミングをバッファリングする

```python
# TestClient は全コンテンツを蓄積してから r.text を返す
r = client.get("/stream/numbers?count=5")
r.text  # → "1\n2\n3\n4\n5\n" (全部まとめて)

# チャンクのタイミングをテストするには httpx.AsyncClient が必要:
async with httpx.AsyncClient(app=app, base_url="http://test") as client:
    async with client.stream("GET", "/stream/numbers") as r:
        async for chunk in r.aiter_bytes():
            ...  # チャンク単位で処理
```

---

## テスト結果（全19件パス）

```
test_stream_numbers_returns_200                      PASSED
test_stream_numbers_content                          PASSED
test_stream_numbers_default_count                    PASSED
test_stream_numbers_invalid_count_uses_default       PASSED
test_stream_events_returns_200                       PASSED
test_stream_events_content_type                      PASSED
test_stream_events_sse_format                        PASSED
test_stream_events_has_cache_control_header          PASSED
test_stream_events_sse_data_is_valid_json            PASSED
test_stream_json_lines_returns_200                   PASSED
test_stream_json_lines_content_type                  PASSED
test_stream_json_lines_each_line_is_json             PASSED
test_stream_csv_returns_200                          PASSED
test_stream_csv_has_header_row                       PASSED
test_stream_csv_content_disposition_header           PASSED
test_streaming_has_request_id_header                 PASSED  ← nene2 共存 ✅
test_streaming_has_security_headers                  PASSED  ← nene2 共存 ✅
test_friction_streaming_response_not_json_response   PASSED
test_friction_testclient_buffers_entire_stream       PASSED
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F91-1 | `StreamingResponse` では `response_model` が使えず OpenAPI スキーマが不完全 | 低 |
| F91-2 | TestClient がストリーミングをバッファリングするためチャンクタイミングのテストが不可 | 低 |

---

## 使用感（主観評価）

### 直感性 ★★★★★

`StreamingResponse` + async generator は直感的でシンプル。
nene2 の `setup_middlewares()` との共存も問題なく、
X-Request-Id やセキュリティヘッダーも自動で付与された。

### 実害の深刻さ ★★☆☆☆

F91-1 は OpenAPI ドキュメントの品質問題のみ。実際の動作には影響しない。
F91-2 は「本当のストリーミングテスト」が書けないが、
ほとんどのユースケースでは TestClient のバッファリングで十分。

### 総合コメント

ストリーミングレスポンスは nene2 と非常に相性が良い。
JSONResponse から StreamingResponse への切り替えは簡単で、
ミドルウェアスタックもそのまま動く。
SSE の `Cache-Control: no-cache` + `X-Accel-Buffering: no` ヘッダーも
FT87 で追加した `headers` パラメーターを使えば `problem_details_response()` でも付けられる。

---

## 推奨アクション

1. **docs**: how-to に「ストリーミングレスポンス」ガイドを追加
   - StreamingResponse / SSE / NDJSON / CSV の実装例
   - `response_model` が使えない旨と、OpenAPI に `description` だけでも付ける方法
   - TestClient でのテスト方法と httpx.AsyncClient での本格テスト方法
