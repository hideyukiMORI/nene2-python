# How-to: CORS 設定

`setup_middlewares()` の `cors_allowed_origins` パラメーターで CORS を有効化する方法を説明する。

---

## 1. 基本: 単一オリジンを許可

```python
from nene2.middleware import setup_middlewares

app = FastAPI()
setup_middlewares(app, cors_allowed_origins=["https://example.com"])
```

`cors_allowed_origins` を指定しない（デフォルト `None`）と CORS ミドルウェアは追加されない。

---

## 2. 複数オリジンを許可

```python
setup_middlewares(app, cors_allowed_origins=[
    "https://app.example.com",
    "https://admin.example.com",
])
```

---

## 3. 開発環境: localhost を許可

```python
import os

origins = ["https://app.example.com"]
if os.getenv("APP_ENV") == "local":
    origins += ["http://localhost:3000", "http://localhost:5173"]

setup_middlewares(app, cors_allowed_origins=origins)
```

**`allow_origins=["*"]` は禁止**。CLAUDE.md のセキュリティポリシーにより、ワイルドカードオリジンは開発環境でも使用不可。

---

## 4. credentials（Cookie・Authorization ヘッダー）を許可

`setup_middlewares()` は内部で `allow_credentials=True` を設定しない。credentials が必要な場合は `CORSMiddleware` を直接追加する。

```python
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
setup_middlewares(app)  # 他のミドルウェア（RequestId 等）は通常通り設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**注意**: `add_middleware` は LIFO のため、`CORSMiddleware` を後から追加すると最外側に配置される。`setup_middlewares()` の後に呼ぶことで、CORS が最も外側で処理される。

---

## 5. CORS とプリフライトリクエスト

`OPTIONS` リクエスト（プリフライト）は `CORSMiddleware` が自動で処理する。`@app.options(...)` を定義する必要はない。

---

## 6. テストでの CORS ヘッダー確認

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
