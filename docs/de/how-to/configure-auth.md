# Authentifizierung konfigurieren

nene2-python unterstützt Bearer-Token- und API-Key-Authentifizierung, beide als Middleware implementiert und über Umgebungsvariablen aktiviert.

## Bearer Token

### Aktivieren

Fügen Sie dies in Ihre `.env`-Datei ein:

```dotenv
BEARER_TOKEN_ENABLED=true
BEARER_TOKENS=["token1","token2","token3"]
```

### Verhalten

- Jede Anfrage muss `Authorization: Bearer <token>` enthalten
- Tokens werden mit `secrets.compare_digest` (zeitkonstant) verglichen
- Ungültige Tokens liefern `401 Unauthorized` (RFC 9457 Problem Details)

### Beispiel

```bash
curl -H "Authorization: Bearer token1" http://localhost:8080/notes
```

## API Key

### Aktivieren

```dotenv
API_KEY_ENABLED=true
API_KEYS=["key1","key2"]
```

### Verhalten

- Jede Anfrage muss `X-Api-Key: <key>` enthalten
- Ungültige Keys liefern `401 Unauthorized`

### Beispiel

```bash
curl -H "X-Api-Key: key1" http://localhost:8080/notes
```

## Beide gleichzeitig verwenden (UND-Bedingung)

Wenn beide Middlewares über `add_middleware` hinzugefügt werden, müssen Anfragen **beide** Prüfungen bestehen (UND-Bedingung). Ein Bearer-Token allein oder ein API-Key allein führt jeweils zu 401.

## Entweder-oder-Authentifizierung (Bearer Token ODER API Key)

Wenn Sie entweder einen Bearer-Token oder einen API-Key akzeptieren möchten — je nachdem, was vorhanden ist — können die eingebauten Middlewares dies nicht ausdrücken. Implementieren Sie eine benutzerdefinierte Middleware, die die vorhandenen Verifizierungslogiken wiederverwendet:

```python
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from nene2.auth import LocalTokenVerifier
from nene2.auth.exceptions import TokenVerificationException
from nene2.http.problem_details import problem_details_response

class EitherOrAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, bearer_tokens: list[str], api_keys: list[str],
                 exclude_paths: list[str] | None = None) -> None:
        super().__init__(app)
        self._bearer = LocalTokenVerifier(bearer_tokens)
        self._api_key = LocalTokenVerifier(api_keys)
        self._exclude_paths = set(exclude_paths or [])

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._exclude_paths:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                if self._bearer.verify(auth[len("Bearer "):]):
                    return await call_next(request)
            except TokenVerificationException:
                pass

        api_key = request.headers.get("X-Api-Key", "")
        if api_key:
            try:
                if self._api_key.verify(api_key):
                    return await call_next(request)
            except TokenVerificationException:
                pass

        return problem_details_response(
            "unauthorized", "Unauthorized", 401,
            "A valid Bearer token or X-Api-Key header is required.",
        )
```

## Auth in Tests deaktivieren

```python
from nene2.config import AppSettings
from fastapi.testclient import TestClient
from example.app import create_app

client = TestClient(create_app(AppSettings(bearer_token_enabled=False)))
```

## Benutzerdefinierter TokenVerifier (z. B. JWT)

Implementieren Sie `TokenVerifierProtocol` und lösen Sie bei Fehler `TokenVerificationException` aus.

```python
from nene2.auth import TokenVerificationException, TokenVerifierProtocol
import jwt

class JwtTokenVerifier:
    def __init__(self, secret: str) -> None:
        self._secret = secret

    def verify(self, token: str) -> bool:
        try:
            jwt.decode(token, self._secret, algorithms=["HS256"])
            return True
        except jwt.InvalidTokenError as exc:
            raise TokenVerificationException(str(exc)) from exc
```

Übergeben Sie Ihren Verifier direkt an `BearerTokenMiddleware`.

## Tokens aus Umgebungsvariablen laden

Verwenden Sie `LocalTokenVerifier.from_env()`, um den Split-und-Strip-Boilerplate zu vermeiden:

```dotenv
# .env
BEARER_TOKENS=token-a,token-b,token-c
```

```python
from nene2.auth import BearerTokenMiddleware, LocalTokenVerifier

app.add_middleware(
    BearerTokenMiddleware,
    verifier=LocalTokenVerifier.from_env("BEARER_TOKENS"),
)
```

Eine nicht gesetzte oder leere Variable erzeugt eine leere Allowlist — alle Anfragen werden abgelehnt.

## Pfade von der Authentifizierung ausschließen

Verwenden Sie `exclude_paths`, um Auth für Health-Checks und API-Dokumentation zu umgehen:

```python
app.add_middleware(
    BearerTokenMiddleware,
    verifier=LocalTokenVerifier.from_env("BEARER_TOKENS"),
    exclude_paths=["/docs", "/openapi.json", "/redoc", "/health"],
)
```

`ApiKeyAuthMiddleware` unterstützt denselben Parameter.

## MCP-Server — bei fehlendem Token sofort fehlschlagen

Wenn ein MCP-Server eine Bearer-geschützte API über `HttpxMcpClient` aufruft, validieren Sie den Token beim Start, statt erst beim Aufruf einen fehlenden Token zu entdecken:

```python
import os
from nene2.mcp.http_client import HttpxMcpClient

token = os.getenv("MCP_BEARER_TOKEN")
if not token:
    raise RuntimeError("MCP_BEARER_TOKEN is not set — cannot call the authenticated API.")
client = HttpxMcpClient(token)
```

## Benutzerdefinierter TokenIssuer (z. B. JWT)

Implementieren Sie `TokenIssuerProtocol`, um Tokens auszustellen (z. B. für einen Login-Endpunkt).

```python
from nene2.auth import TokenIssuerProtocol
import jwt

class JwtTokenIssuer:
    def __init__(self, secret: str) -> None:
        self._secret = secret

    def issue(self, claims: dict[str, object]) -> str:
        return jwt.encode(claims, self._secret, algorithm="HS256")
```
