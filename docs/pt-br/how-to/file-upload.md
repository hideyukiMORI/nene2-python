# Como fazer: upload de arquivo

Padrões de upload de arquivo usando o `UploadFile` do FastAPI.

---

## 1. Padrão básico

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

**`await file.read()` requer `async def`.** Não pode ser usado em um handler `def` (síncrono).

---

## 2. Validando o tipo de conteúdo

O FastAPI não valida `content_type` automaticamente. Verifique manualmente.

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

## 3. Validando por magic bytes (assinatura do arquivo)

O header Content-Type pode ser falsificado. Verifique o formato do arquivo pelos seus
bytes iniciais (magic bytes).

```python
MAGIC_BYTES: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # WebP usa um header RIFF
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

## 4. Limites de tamanho de arquivo

O parâmetro `max_request_bytes` de `setup_middlewares()` limita o tamanho de todas
as requisições.

```python
setup_middlewares(app, max_request_bytes=10 * 1024 * 1024)  # 10 MB
```

Para limitar por endpoint, verifique manualmente:

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

## 5. Testando

```python
from io import BytesIO
from fastapi.testclient import TestClient

def test_upload_image() -> None:
    # JPEG válido mínimo (magic bytes JPEG)
    fake_jpeg = b"\xff\xd8\xff" + b"\x00" * 100
    r = client.post(
        "/images",
        files={"file": ("test.jpg", BytesIO(fake_jpeg), "image/jpeg")},
    )
    assert r.status_code == 201
```

Passe uma tupla `(filename, fileobj, content_type)` via o parâmetro `files=`.

---

## Observação: o parâmetro se chama `max_request_bytes`

O parâmetro de `setup_middlewares()` é `max_request_bytes` (uma contagem em bytes).
`max_request_size` não existe.

```python
# ✅ correto
setup_middlewares(app, max_request_bytes=10_000_000)

# ❌ TypeError
setup_middlewares(app, max_request_size=10_000_000)
```
