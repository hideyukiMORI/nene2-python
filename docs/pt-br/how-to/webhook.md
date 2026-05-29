# Como fazer: receber webhooks e verificar assinaturas HMAC-SHA256

Um padrão para receber webhooks de serviços externos como GitHub ou Stripe
e verificar suas assinaturas HMAC-SHA256.

---

## 1. Padrão básico (estilo GitHub)

O GitHub envia a assinatura em um header `X-Hub-Signature-256: sha256=<hex>`.

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
    # ... processar o evento
    return JSONResponse({"status": "received", "event": event})
```

---

## 2. Estilo Stripe (assinatura com timestamp)

O Stripe envia `Stripe-Signature: t=<timestamp>,v1=<hex>`. Você faz HMAC do timestamp +
body.

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

    # estilo Stripe: HMAC de "timestamp." + body
    signed_payload = f"{timestamp}.".encode() + body
    if not verify_hmac_signature(signed_payload, WEBHOOK_SECRET, v1_sig):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)

    payload = await request.json()
    return JSONResponse({"status": "received", "type": payload.get("type")})
```

---

## 3. Leitura dupla: `await request.body()` → `await request.json()`

A verificação de assinatura precisa dos bytes brutos (`body()`), mas você também quer fazer
parse como JSON depois. O FastAPI armazena em cache o body internamente, então você pode chamar ambos.

```python
@app.post("/webhooks/example")
async def handler(request: Request) -> JSONResponse:
    # ✅ json() ainda funciona mesmo após chamar body() primeiro
    body = await request.body()        # bytes brutos (para verificação de assinatura)
    payload = await request.json()     # parse JSON (usa o cache interno)
    return JSONResponse({"size": len(body), "action": payload.get("action")})
```

`json.loads(body)` também funciona, mas `await request.json()` é mais consistente com
a conversão de modelo Pydantic.

---

## 4. A API `verify_hmac_signature()`

```python
from nene2.security import verify_hmac_signature

verify_hmac_signature(
    body: bytes,       # os bytes a verificar
    secret: str,       # o segredo compartilhado
    signature: str,    # a string de assinatura a verificar (prefixo permitido)
    *,
    prefix: str = "",  # o prefixo da assinatura (ex: "sha256=")
) -> bool
```

Protegida contra timing attacks via `hmac.compare_digest()`. Não use `==` para
comparar assinaturas.

---

## 5. Quando usar este vs. BearerTokenMiddleware

| Padrão | Método de auth | Suporte nene2 |
|---|---|---|
| Auth de cliente API | `Authorization: Bearer <token>` | `BearerTokenMiddleware` |
| Verificação de assinatura de webhook | body da requisição + segredo | `verify_hmac_signature()` |

Adicione endpoints de webhook ao `exclude_paths` do `BearerTokenMiddleware` e faça
sua própria verificação de assinatura. Como o middleware lê o body bruto,
`BearerTokenMiddleware` não pode ser usado nele.

```python
from nene2.middleware import BearerTokenMiddleware

app.add_middleware(
    BearerTokenMiddleware,
    verifier=token_verifier,
    exclude_paths=["/webhooks/"],  # excluir endpoints de webhook
)
```

---

## 6. Testando

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
