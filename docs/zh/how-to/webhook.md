# 操作指南：接收 Webhook 并验证 HMAC-SHA256 签名

接收来自 GitHub 或 Stripe 等外部服务的 Webhook 并验证其 HMAC-SHA256 签名的模式。

---

## 1. 基本模式（GitHub 风格）

GitHub 在 `X-Hub-Signature-256: sha256=<hex>` 头部中发送签名。

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from nene2.security import verify_hmac_signature

WEBHOOK_SECRET = "your-secret-key"

app = FastAPI()

@app.post("/webhooks/github")
async def github_webhook(request: Request) -> JSONResponse:
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()

    if not signature:
        return JSONResponse({"error": "Missing signature"}, status_code=400)

    if not verify_hmac_signature(body, WEBHOOK_SECRET, signature, prefix="sha256="):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)

    payload = await request.json()
    event = request.headers.get("X-GitHub-Event", "unknown")
    # ... 处理事件
    return JSONResponse({"status": "received", "event": event})
```

---

## 2. Stripe 风格（带时间戳的签名）

Stripe 发送 `Stripe-Signature: t=<timestamp>,v1=<hex>`，对时间戳 + 请求体进行 HMAC 签名。

```python
import hashlib
import hmac
import time

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> JSONResponse:
    stripe_sig = request.headers.get("Stripe-Signature", "")
    body = await request.body()

    if not stripe_sig:
        return JSONResponse({"error": "Missing Stripe-Signature"}, status_code=400)

    parts = dict(item.split("=", 1) for item in stripe_sig.split(",") if "=" in item)
    timestamp = parts.get("t", "")
    v1_sig = parts.get("v1", "")

    # Stripe 风格：对 "timestamp." + body 进行 HMAC
    signed_payload = f"{timestamp}.".encode() + body
    if not verify_hmac_signature(signed_payload, WEBHOOK_SECRET, v1_sig):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)

    payload = await request.json()
    return JSONResponse({"status": "received", "type": payload.get("type")})
```

---

## 3. 重复读取：`await request.body()` → `await request.json()`

签名验证需要原始字节（`body()`），之后还要将其解析为 JSON。FastAPI 在内部缓存请求体，因此可以同时调用两者。

```python
@app.post("/webhooks/example")
async def handler(request: Request) -> JSONResponse:
    # ✅ 先调用 body() 后，json() 仍然有效
    body = await request.body()        # 原始字节（用于签名验证）
    payload = await request.json()     # JSON 解析（使用内部缓存）
    return JSONResponse({"size": len(body), "action": payload.get("action")})
```

`json.loads(body)` 也可以，但 `await request.json()` 与 Pydantic 模型转换更一致。

---

## 4. `verify_hmac_signature()` API

```python
from nene2.security import verify_hmac_signature

verify_hmac_signature(
    body: bytes,       # 要验证的字节
    secret: str,       # 共享密钥
    signature: str,    # 要验证的签名字符串（允许前缀）
    *,
    prefix: str = "",  # 签名前缀（例如 "sha256="）
) -> bool
```

通过 `hmac.compare_digest()` 防止时序攻击。不要使用 `==` 比较签名。

---

## 5. 何时使用此方案 vs. BearerTokenMiddleware

| 模式 | 认证方式 | nene2 支持 |
|---|---|---|
| API 客户端认证 | `Authorization: Bearer <token>` | `BearerTokenMiddleware` |
| Webhook 签名验证 | 请求体 + 密钥 | `verify_hmac_signature()` |

将 Webhook endpoint 添加到 `BearerTokenMiddleware` 的 `exclude_paths` 中，并自行进行签名验证。因为 middleware 读取原始请求体，`BearerTokenMiddleware` 无法用于 Webhook endpoint。

```python
from nene2.middleware import BearerTokenMiddleware

app.add_middleware(
    BearerTokenMiddleware,
    verifier=token_verifier,
    exclude_paths=["/webhooks/"],  # 排除 Webhook endpoint
)
```

---

## 6. 测试

```python
import hashlib
import hmac

def make_github_sig(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

def test_webhook_valid() -> None:
    payload = b'{"action": "opened"}'
    r = client.post(
        "/webhooks/github",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": make_github_sig(payload, "your-secret-key"),
            "X-GitHub-Event": "issues",
        },
    )
    assert r.status_code == 200
```
