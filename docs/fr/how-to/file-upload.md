# Guide pratique : upload de fichiers

Schémas d'upload de fichiers avec `UploadFile` de FastAPI.

---

## 1. Schéma de base

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

**`await file.read()` nécessite `async def`.** Il ne peut pas être utilisé dans un handler
`def` (synchrone).

---

## 2. Valider le type de contenu

FastAPI ne valide pas `content_type` automatiquement. Vérifiez-le manuellement.

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

## 3. Valider par magic bytes (signature de fichier)

L'en-tête Content-Type peut être falsifié. Vérifiez le format du fichier par ses octets de tête (magic bytes).

```python
MAGIC_BYTES: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # WebP utilise un en-tête RIFF
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

## 4. Limites de taille de fichier

Le paramètre `max_request_bytes` de `setup_middlewares()` limite la taille de toutes les requêtes.

```python
setup_middlewares(app, max_request_bytes=10 * 1024 * 1024)  # 10 Mo
```

Pour limiter par endpoint, vérifiez manuellement :

```python
MAX_SIZE = 5 * 1024 * 1024  # 5 Mo

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
    # JPEG valide minimal (magic bytes JPEG)
    fake_jpeg = b"\xff\xd8\xff" + b"\x00" * 100
    r = client.post(
        "/images",
        files={"file": ("test.jpg", BytesIO(fake_jpeg), "image/jpeg")},
    )
    assert r.status_code == 201
```

Passez un tuple `(filename, fileobj, content_type)` via le paramètre `files=`.

---

## Note : le paramètre s'appelle `max_request_bytes`

Le paramètre de `setup_middlewares()` est `max_request_bytes` (un nombre d'octets).
`max_request_size` n'existe pas.

```python
# ✅ correct
setup_middlewares(app, max_request_bytes=10_000_000)

# ❌ TypeError
setup_middlewares(app, max_request_size=10_000_000)
```
