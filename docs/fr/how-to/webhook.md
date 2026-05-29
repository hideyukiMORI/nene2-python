# Guide pratique : recevoir des webhooks et vérifier les signatures HMAC-SHA256

Un schéma pour recevoir des webhooks de services externes comme GitHub ou Stripe et vérifier
leurs signatures HMAC-SHA256.

---

## 1. Schéma de base (style GitHub)

GitHub envoie la signature dans un en-tête `X-Hub-Signature-256: sha256=<hex>`.

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
    # ... traiter l'événement
    return JSONResponse({"status": "received", "event": event})
```

---

## 2. Style Stripe (signature avec timestamp)

Stripe envoie `Stripe-Signature: t=<timestamp>,v1=<hex>`. Vous faites un HMAC du timestamp +
du corps.

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

    # Style Stripe : HMAC de "timestamp." + body
    signed_payload = f"{timestamp}.".encode() + body
    if not verify_hmac_signature(signed_payload, WEBHOOK_SECRET, v1_sig):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)

    payload = await request.json()
    return JSONResponse({"status": "received", "type": payload.get("type")})
```

---

## 3. Double lecture : `await request.body()` → `await request.json()`

La vérification de signature nécessite les octets bruts (`body()`), mais vous souhaitez aussi
l'analyser en JSON ensuite. FastAPI met le corps en cache en interne, vous pouvez donc appeler
les deux.

```python
@app.post("/webhooks/example")
async def handler(request: Request) -> JSONResponse:
    # ✅ json() fonctionne encore même après avoir appelé body() en premier
    body = await request.body()        # octets bruts (pour la vérification de signature)
    payload = await request.json()     # analyse JSON (utilise le cache interne)
    return JSONResponse({"size": len(body), "action": payload.get("action")})
```

`json.loads(body)` fonctionne aussi, mais `await request.json()` est plus cohérent avec la
conversion de modèle Pydantic.

---

## 4. L'API `verify_hmac_signature()`

```python
from nene2.security import verify_hmac_signature

verify_hmac_signature(
    body: bytes,       # les octets à vérifier
    secret: str,       # le secret partagé
    signature: str,    # la chaîne de signature à vérifier (préfixe autorisé)
    *,
    prefix: str = "",  # le préfixe de signature (p. ex. "sha256=")
) -> bool
```

Protégé contre les attaques temporelles via `hmac.compare_digest()`. N'utilisez pas `==` pour
comparer les signatures.

---

## 5. Quand utiliser ceci vs. BearerTokenMiddleware

| Schéma | Méthode d'auth | Support nene2 |
|---|---|---|
| Auth de client API | `Authorization: Bearer <token>` | `BearerTokenMiddleware` |
| Vérification de signature webhook | corps de requête + secret | `verify_hmac_signature()` |

Ajoutez les endpoints webhook à `exclude_paths` de `BearerTokenMiddleware` et faites votre
propre vérification de signature. Comme le middleware lit le corps brut, `BearerTokenMiddleware`
ne peut pas être utilisé dessus.

```python
from nene2.middleware import BearerTokenMiddleware

app.add_middleware(
    BearerTokenMiddleware,
    verifier=token_verifier,
    exclude_paths=["/webhooks/"],  # exclure les endpoints webhook
)
```

---

## 6. Tests

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
