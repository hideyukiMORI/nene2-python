# 操作指南：CORS 配置

通过 `setup_middlewares()` 的 `cors_allowed_origins` 参数启用 CORS。

---

## 1. 基础：允许单个来源

```python
from nene2.middleware import setup_middlewares

app = FastAPI()
setup_middlewares(app, cors_allowed_origins=["https://example.com"])
```

若省略 `cors_allowed_origins`（默认 `None`），则不添加 CORS middleware。

---

## 2. 允许多个来源

```python
setup_middlewares(app, cors_allowed_origins=[
    "https://app.example.com",
    "https://admin.example.com",
])
```

---

## 3. 开发环境：允许 localhost

```python
import os

origins = ["https://app.example.com"]
if os.getenv("APP_ENV") == "local":
    origins += ["http://localhost:3000", "http://localhost:5173"]

setup_middlewares(app, cors_allowed_origins=origins)
```

**禁止使用 `allow_origins=["*"]`。** 根据 CLAUDE.md 安全策略，不得使用通配符来源 — 开发环境也不例外。

---

## 4. 允许凭据（Cookie、Authorization 头）

`setup_middlewares()` 内部不设置 `allow_credentials=True`。如果需要凭据，直接添加 `CORSMiddleware`。

```python
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
setup_middlewares(app)  # 其他 middleware（RequestId 等）照常
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**注意**：`add_middleware` 遵循 LIFO 顺序，最后添加的 `CORSMiddleware` 位于最外层。在 `setup_middlewares()` 之后调用，使 CORS 运行在外层。

---

## 5. CORS 与预检请求

`OPTIONS` 请求（预检）由 `CORSMiddleware` 自动处理，无需定义 `@app.options(...)`。

---

## 6. 在测试中检查 CORS 头

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
