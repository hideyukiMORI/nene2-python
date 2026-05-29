# Configurer l'authentification

nene2-python prend en charge l'authentification par Bearer Token et par clé API, toutes deux
implémentées sous forme de middleware et activées via des variables d'environnement.

## Bearer Token

### Activation

Ajoutez dans votre fichier `.env` :

```dotenv
BEARER_TOKEN_ENABLED=true
BEARER_TOKENS=["token1","token2","token3"]
```

### Comportement

- Chaque requête doit inclure `Authorization: Bearer <token>`
- Les tokens sont comparés avec `secrets.compare_digest` (protection contre les attaques temporelles)
- Les tokens invalides retournent `401 Unauthorized` (RFC 9457 Problem Details)

### Exemple

```bash
curl -H "Authorization: Bearer token1" http://localhost:8080/notes
```

## Clé API

### Activation

```dotenv
API_KEY_ENABLED=true
API_KEYS=["key1","key2"]
```

### Comportement

- Chaque requête doit inclure `X-Api-Key: <key>`
- Les clés invalides retournent `401 Unauthorized`

### Exemple

```bash
curl -H "X-Api-Key: key1" http://localhost:8080/notes
```

## Utiliser les deux simultanément (condition ET)

Quand les deux middlewares sont ajoutés via `add_middleware`, les requêtes doivent passer **les deux**
vérifications (condition ET). Un Bearer token seul ou une clé API seule resulte en 401.

## Authentification exclusive (Bearer Token OU clé API)

Si vous souhaitez accepter **soit** un Bearer token, **soit** une clé API — selon ce qui est présent
— les middlewares intégrés ne peuvent pas exprimer cela. Implémentez un middleware personnalisé qui
réutilise les vérificateurs existants :

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

## Désactiver l'auth dans les tests

```python
from nene2.config import AppSettings
from fastapi.testclient import TestClient
from example.app import create_app

client = TestClient(create_app(AppSettings(bearer_token_enabled=False)))
```

## TokenVerifier personnalisé (p. ex. JWT)

Implémentez `TokenVerifierProtocol` et levez `TokenVerificationException` en cas d'échec.

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

Passez votre vérificateur directement à `BearerTokenMiddleware`.

## Charger les tokens depuis les variables d'environnement

Utilisez `LocalTokenVerifier.from_env()` pour éviter d'écrire le code de découpage et nettoyage à chaque fois :

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

Une variable non définie ou vide produit une allowlist vide — toutes les requêtes sont refusées.

## Exclure des chemins de l'authentification

Utilisez `exclude_paths` pour contourner l'auth pour les health checks et la doc de l'API :

```python
app.add_middleware(
    BearerTokenMiddleware,
    verifier=LocalTokenVerifier.from_env("BEARER_TOKENS"),
    exclude_paths=["/docs", "/openapi.json", "/redoc", "/health"],
)
```

`ApiKeyAuthMiddleware` prend en charge le même paramètre.

## Serveur MCP — échec rapide sur token manquant

Quand un serveur MCP appelle une API protégée par Bearer via `HttpxMcpClient`, validez le token
au démarrage plutôt que de découvrir un token manquant lors de l'appel :

```python
import os
from nene2.mcp.http_client import HttpxMcpClient

token = os.getenv("MCP_BEARER_TOKEN")
if not token:
    raise RuntimeError("MCP_BEARER_TOKEN is not set — cannot call the authenticated API.")
client = HttpxMcpClient(token)
```

## TokenIssuer personnalisé (p. ex. JWT)

Implémentez `TokenIssuerProtocol` pour émettre des tokens (p. ex. pour un endpoint de login).

```python
from nene2.auth import TokenIssuerProtocol
import jwt

class JwtTokenIssuer:
    def __init__(self, secret: str) -> None:
        self._secret = secret

    def issue(self, claims: dict[str, object]) -> str:
        return jwt.encode(claims, self._secret, algorithm="HS256")
```
