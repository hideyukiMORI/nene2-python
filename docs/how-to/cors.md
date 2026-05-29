# How-to: CORS configuration

How to enable CORS via the `cors_allowed_origins` parameter of `setup_middlewares()`.

---

## 1. Basics: allow a single origin

```python
from nene2.middleware import setup_middlewares

app = FastAPI()
setup_middlewares(app, cors_allowed_origins=["https://example.com"])
```

If `cors_allowed_origins` is omitted (default `None`), the CORS middleware is not added.

---

## 2. Allow multiple origins

```python
setup_middlewares(app, cors_allowed_origins=[
    "https://app.example.com",
    "https://admin.example.com",
])
```

---

## 3. Development: allow localhost

```python
import os

origins = ["https://app.example.com"]
if os.getenv("APP_ENV") == "local":
    origins += ["http://localhost:3000", "http://localhost:5173"]

setup_middlewares(app, cors_allowed_origins=origins)
```

**`allow_origins=["*"]` is forbidden.** Per the CLAUDE.md security policy, a
wildcard origin must not be used — not even in development.

---

## 4. Allow credentials (cookies, Authorization header)

`setup_middlewares()` does not set `allow_credentials=True` internally. If you need
credentials, add `CORSMiddleware` directly.

```python
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
setup_middlewares(app)  # other middleware (RequestId, etc.) as usual
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Note**: `add_middleware` is LIFO, so adding `CORSMiddleware` last places it
outermost. Calling it after `setup_middlewares()` makes CORS run on the outside.

---

## 5. CORS and preflight requests

`OPTIONS` requests (preflight) are handled automatically by `CORSMiddleware`. You
do not need to define `@app.options(...)`.

---

## 6. Checking CORS headers in tests

```python
def test_cors_header() -> None:
    with TestClient(app) as client:
        r = client.get("/items", headers={"Origin": "https://app.example.com"})
        assert r.headers.get("access-control-allow-origin") == "https://app.example.com"

def test_cors_not_allowed_for_unknown_origin() -> None:
    with TestClient(app) as client:
        r = client.get("/items", headers={"Origin": "https://evil.com"})
        assert "access-control-allow-origin" not in r.headers
```
