# How-to: Datei-Upload

Datei-Upload-Muster mit FastAPIs `UploadFile`.

---

## 1. Grundlegendes Muster

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

**`await file.read()` erfordert `async def`.** Es kann nicht in einem `def`-(synchronen) Handler verwendet werden.

---

## 2. Den Content-Type validieren

FastAPI validiert `content_type` nicht automatisch. Prüfen Sie ihn manuell.

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

## 3. Validierung anhand von Magic Bytes (Dateisignatur)

Der Content-Type-Header kann gefälscht werden. Überprüfen Sie das Dateiformat anhand seiner führenden Bytes (Magic Bytes).

```python
MAGIC_BYTES: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # WebP verwendet einen RIFF-Header
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

## 4. Dateigrößenbeschränkungen

Der Parameter `max_request_bytes` von `setup_middlewares()` begrenzt die Größe aller Anfragen.

```python
setup_middlewares(app, max_request_bytes=10 * 1024 * 1024)  # 10 MB
```

Zur Begrenzung pro Endpunkt prüfen Sie manuell:

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

## 5. Tests

```python
from io import BytesIO
from fastapi.testclient import TestClient

def test_upload_image() -> None:
    # minimales gültiges JPEG (JPEG Magic Bytes)
    fake_jpeg = b"\xff\xd8\xff" + b"\x00" * 100
    r = client.post(
        "/images",
        files={"file": ("test.jpg", BytesIO(fake_jpeg), "image/jpeg")},
    )
    assert r.status_code == 201
```

Übergeben Sie ein `(filename, fileobj, content_type)`-Tupel über den `files=`-Parameter.

---

## Hinweis: Der Parameter heißt `max_request_bytes`

Der `setup_middlewares()`-Parameter ist `max_request_bytes` (eine Byte-Anzahl). `max_request_size` existiert nicht.

```python
# ✅ korrekt
setup_middlewares(app, max_request_bytes=10_000_000)

# ❌ TypeError
setup_middlewares(app, max_request_size=10_000_000)
```
