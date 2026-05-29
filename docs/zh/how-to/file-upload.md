# 操作指南：文件上传

使用 FastAPI 的 `UploadFile` 处理文件上传的模式。

---

## 1. 基本模式

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

**`await file.read()` 要求使用 `async def`。** 不能在 `def`（同步）handler 中使用。

---

## 2. 验证内容类型

FastAPI 不会自动验证 `content_type`，需手动检查。

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

## 3. 通过魔术字节（文件签名）验证

Content-Type 头可以被伪造。通过文件的起始字节（魔术字节）验证文件格式。

```python
MAGIC_BYTES: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # WebP 使用 RIFF 头
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

## 4. 文件大小限制

`setup_middlewares()` 的 `max_request_bytes` 参数限制所有请求的大小。

```python
setup_middlewares(app, max_request_bytes=10 * 1024 * 1024)  # 10 MB
```

若要按 endpoint 限制，可手动检查：

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

## 5. 测试

```python
from io import BytesIO
from fastapi.testclient import TestClient

def test_upload_image() -> None:
    # 最小有效 JPEG（JPEG 魔术字节）
    fake_jpeg = b"\xff\xd8\xff" + b"\x00" * 100
    r = client.post(
        "/images",
        files={"file": ("test.jpg", BytesIO(fake_jpeg), "image/jpeg")},
    )
    assert r.status_code == 201
```

通过 `files=` 参数传入 `(filename, fileobj, content_type)` 元组。

---

## 注意：参数名为 `max_request_bytes`

`setup_middlewares()` 的参数是 `max_request_bytes`（字节数）。`max_request_size` 不存在。

```python
# ✅ 正确
setup_middlewares(app, max_request_bytes=10_000_000)

# ❌ TypeError
setup_middlewares(app, max_request_size=10_000_000)
```
