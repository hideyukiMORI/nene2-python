# How-to: Webhook 受信と HMAC-SHA256 署名検証

GitHub や Stripe などの外部サービスから Webhook を受信し、HMAC-SHA256 署名を検証するパターンを説明する。

---

## 1. 基本パターン（GitHub 方式）

GitHub は `X-Hub-Signature-256: sha256=<hex>` ヘッダーで署名を送る。

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
    # ... イベント処理
    return JSONResponse({"status": "received", "event": event})
```

---

## 2. Stripe 方式（timestamp 付き署名）

Stripe は `Stripe-Signature: t=<timestamp>,v1=<hex>` 形式で送る。timestamp + body を HMAC する。

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

    # Stripe 方式: "timestamp." + body を HMAC する
    signed_payload = f"{timestamp}.".encode() + body
    if not verify_hmac_signature(signed_payload, WEBHOOK_SECRET, v1_sig):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)

    payload = await request.json()
    return JSONResponse({"status": "received", "type": payload.get("type")})
```

---

## 3. `await request.body()` → `await request.json()` の二重読み取り

署名検証では生バイト（`body()`）が必要だが、その後 JSON としてもパースしたい。
FastAPI はボディを内部でキャッシュするので、両方呼び出せる。

```python
@app.post("/webhooks/example")
async def handler(request: Request) -> JSONResponse:
    # ✅ body() を先に呼んでも json() は正常に動く
    body = await request.body()        # 生バイト取得（署名検証用）
    payload = await request.json()     # JSON パース（内部キャッシュを使う）
    return JSONResponse({"size": len(body), "action": payload.get("action")})
```

`json.loads(body)` でも動作するが、`await request.json()` の方が Pydantic モデル変換と統一感がある。

---

## 4. `verify_hmac_signature()` の API

```python
from nene2.security import verify_hmac_signature

verify_hmac_signature(
    body: bytes,       # 検証するバイト列
    secret: str,       # 共有シークレット
    signature: str,    # 検証対象の署名文字列（prefix 込み可）
    *,
    prefix: str = "",  # 署名の prefix（例: "sha256="）
) -> bool
```

`hmac.compare_digest()` で timing attack 対策済み。署名の比較に `==` を使わないこと。

---

## 5. BearerTokenMiddleware との使い分け

| パターン | 認証方法 | nene2 サポート |
|---|---|---|
| API クライアント認証 | `Authorization: Bearer <token>` | `BearerTokenMiddleware` |
| Webhook 署名検証 | リクエストボディ + シークレット | `verify_hmac_signature()` |

Webhook エンドポイントは `BearerTokenMiddleware` の `exclude_paths` に加えて、
自前の署名検証を行う。ミドルウェアでは raw body を読む関係で `BearerTokenMiddleware` は使用できない。

```python
from nene2.middleware import BearerTokenMiddleware

app.add_middleware(
    BearerTokenMiddleware,
    verifier=token_verifier,
    exclude_paths=["/webhooks/"],  # Webhook エンドポイントを除外
)
```

---

## 6. テスト

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
