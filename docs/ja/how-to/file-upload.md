# How-to: ファイルアップロード

FastAPI の `UploadFile` を使ったファイルアップロードパターンを説明する。

---

## 1. 基本パターン

```python
from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/upload", status_code=201)
async def upload_file(file: UploadFile) -> JSONResponse:
    content = await file.read()
    return JSONResponse({
        "filename": file.filename,
        "size": len(content),
        "content_type": file.content_type,
    }, status_code=201)
```

**`await file.read()` は `async def` が必要**。`def`（同期）ハンドラーでは使えない。

---

## 2. コンテントタイプの検証

FastAPI は `content_type` を自動検証しない。手動でチェックする。

```python
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

@app.post("/images", status_code=201)
async def upload_image(file: UploadFile) -> JSONResponse:
    if file.content_type not in ALLOWED_TYPES:
        return problem_details_response(
            "invalid-content-type",
            "Invalid Content Type",
            415,
            f"Allowed types: {', '.join(ALLOWED_TYPES)}",
        )
    content = await file.read()
    return JSONResponse({"filename": file.filename, "size": len(content)}, status_code=201)
```

---

## 3. マジックバイト（ファイルシグネチャ）による検証

Content-Type ヘッダーは偽装できる。ファイルの先頭バイト（マジックバイト）でファイル形式を確認する。

```python
MAGIC_BYTES: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # WebP は RIFF ヘッダー
}

def detect_image_type(data: bytes) -> str | None:
    for magic, mime_type in MAGIC_BYTES.items():
        if data.startswith(magic):
            return mime_type
    return None

@app.post("/images/secure", status_code=201)
async def upload_image_secure(file: UploadFile) -> JSONResponse:
    content = await file.read()
    detected = detect_image_type(content)
    if detected is None:
        return problem_details_response(
            "invalid-file-type", "Invalid File Type", 415,
            "Only JPEG, PNG, WebP are allowed.",
        )
    return JSONResponse({
        "filename": file.filename,
        "detected_type": detected,
        "size": len(content),
    }, status_code=201)
```

---

## 4. ファイルサイズ制限

`setup_middlewares()` の `max_request_bytes` パラメーターで全リクエストのサイズを制限できる。

```python
setup_middlewares(app, max_request_bytes=10 * 1024 * 1024)  # 10 MB
```

エンドポイントごとに制限したい場合は手動チェック:

```python
MAX_SIZE = 5 * 1024 * 1024  # 5 MB

@app.post("/upload")
async def upload(file: UploadFile) -> JSONResponse:
    content = await file.read()
    if len(content) > MAX_SIZE:
        return problem_details_response(
            "file-too-large", "File Too Large", 413,
            f"Maximum file size is {MAX_SIZE // 1024 // 1024} MB.",
        )
    ...
```

---

## 5. テスト

```python
from io import BytesIO
from fastapi.testclient import TestClient

def test_upload_image() -> None:
    # 最小有効 JPEG（JPEG マジックバイト）
    fake_jpeg = b"\xff\xd8\xff" + b"\x00" * 100
    r = client.post(
        "/images",
        files={"file": ("test.jpg", BytesIO(fake_jpeg), "image/jpeg")},
    )
    assert r.status_code == 201
```

`files=` パラメーターで `(filename, fileobj, content_type)` のタプルを渡す。

---

## 注意: `max_request_bytes` のパラメーター名

`setup_middlewares()` のパラメーター名は `max_request_bytes`（バイト数）。`max_request_size` は存在しない。

```python
# ✅ 正しい
setup_middlewares(app, max_request_bytes=10_000_000)

# ❌ TypeError
setup_middlewares(app, max_request_size=10_000_000)
```
