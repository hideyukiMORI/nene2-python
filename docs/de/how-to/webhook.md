# How-to: Webhooks empfangen und HMAC-SHA256-Signaturen verifizieren

Ein Muster zum Empfangen von Webhooks von externen Diensten wie GitHub oder Stripe und zur Verifizierung ihrer HMAC-SHA256-Signaturen.

---

## 1. Grundlegendes Muster (GitHub-Stil)

GitHub sendet die Signatur in einem `X-Hub-Signature-256: sha256=<hex>`-Header.

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
    # ... Ereignis verarbeiten
    return JSONResponse({"status": "received", "event": event})
```

---

## 2. Stripe-Stil (Signatur mit Zeitstempel)

Stripe sendet `Stripe-Signature: t=<timestamp>,v1=<hex>`. Sie HMAC-en den Zeitstempel + Body.

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

    # Stripe-Stil: HMAC von "timestamp." + body
    signed_payload = f"{timestamp}.".encode() + body
    if not verify_hmac_signature(signed_payload, WEBHOOK_SECRET, v1_sig):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)

    payload = await request.json()
    return JSONResponse({"status": "received", "type": payload.get("type")})
```

---

## 3. Doppeltes Lesen: `await request.body()` → `await request.json()`

Die Signaturverifizierung benötigt die rohen Bytes (`body()`), aber Sie möchten sie danach auch als JSON parsen. FastAPI cached den Body intern, sodass Sie beide aufrufen können.

```python
@app.post("/webhooks/example")
async def handler(request: Request) -> JSONResponse:
    # ✅ json() funktioniert auch nach dem vorherigen Aufruf von body()
    body = await request.body()        # rohe Bytes (für Signaturverifizierung)
    payload = await request.json()     # JSON-Parse (verwendet den internen Cache)
    return JSONResponse({"size": len(body), "action": payload.get("action")})
```

`json.loads(body)` funktioniert ebenfalls, aber `await request.json()` ist konsistenter mit der Pydantic-Modellkonvertierung.

---

## 4. Die `verify_hmac_signature()`-API

```python
from nene2.security import verify_hmac_signature

verify_hmac_signature(
    body: bytes,       # die zu verifizierenden Bytes
    secret: str,       # das gemeinsame Geheimnis
    signature: str,    # der zu verifizierende Signatur-String (Präfix erlaubt)
    *,
    prefix: str = "",  # das Signatur-Präfix (z. B. "sha256=")
) -> bool
```

Gegen Timing-Angriffe geschützt durch `hmac.compare_digest()`. Verwenden Sie nicht `==` zum Vergleichen von Signaturen.

---

## 5. Wann dieses Muster vs. BearerTokenMiddleware verwenden

| Muster | Auth-Methode | nene2-Unterstützung |
|---|---|---|
| API-Client-Auth | `Authorization: Bearer <token>` | `BearerTokenMiddleware` |
| Webhook-Signaturverifizierung | Request-Body + Geheimnis | `verify_hmac_signature()` |

Fügen Sie Webhook-Endpunkte zu `BearerTokenMiddleware`s `exclude_paths` hinzu und führen Sie Ihre eigene Signaturverifizierung durch. Da die Middleware den rohen Body liest, kann `BearerTokenMiddleware` nicht dafür verwendet werden.

```python
from nene2.middleware import BearerTokenMiddleware

app.add_middleware(
    BearerTokenMiddleware,
    verifier=token_verifier,
    exclude_paths=["/webhooks/"],  # Webhook-Endpunkte ausschließen
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
