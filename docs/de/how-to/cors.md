# How-to: CORS-Konfiguration

So aktivieren Sie CORS über den Parameter `cors_allowed_origins` von `setup_middlewares()`.

---

## 1. Grundlagen: einen einzelnen Origin erlauben

```python
from nene2.middleware import setup_middlewares

app = FastAPI()
setup_middlewares(app, cors_allowed_origins=["https://example.com"])
```

Wird `cors_allowed_origins` weggelassen (Standard `None`), wird die CORS-Middleware nicht hinzugefügt.

---

## 2. Mehrere Origins erlauben

```python
setup_middlewares(app, cors_allowed_origins=[
    "https://app.example.com",
    "https://admin.example.com",
])
```

---

## 3. Entwicklung: localhost erlauben

```python
import os

origins = ["https://app.example.com"]
if os.getenv("APP_ENV") == "local":
    origins += ["http://localhost:3000", "http://localhost:5173"]

setup_middlewares(app, cors_allowed_origins=origins)
```

**`allow_origins=["*"]` ist verboten.** Gemäß der CLAUDE.md-Sicherheitsrichtlinie darf kein Wildcard-Origin verwendet werden — auch nicht in der Entwicklung.

---

## 4. Credentials erlauben (Cookies, Authorization-Header)

`setup_middlewares()` setzt intern kein `allow_credentials=True`. Wenn Sie Credentials benötigen, fügen Sie `CORSMiddleware` direkt hinzu.

```python
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
setup_middlewares(app)  # andere Middleware (RequestId, usw.) wie gewohnt
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Hinweis**: `add_middleware` ist LIFO, daher wird `CORSMiddleware` zuletzt hinzugefügt und ist am äußersten. Ein Aufruf nach `setup_middlewares()` lässt CORS außen laufen.

---

## 5. CORS und Preflight-Anfragen

`OPTIONS`-Anfragen (Preflight) werden automatisch von `CORSMiddleware` behandelt. Sie müssen `@app.options(...)` nicht definieren.

---

## 6. CORS-Header in Tests prüfen

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
