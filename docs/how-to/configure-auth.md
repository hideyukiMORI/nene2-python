# Configure authentication

nene2-python supports Bearer Token and API Key authentication, both implemented as middleware and enabled via environment variables.

## Bearer Token

### Enable

Add to your `.env` file:

```dotenv
BEARER_TOKEN_ENABLED=true
BEARER_TOKENS=["token1","token2","token3"]
```

### Behaviour

- Every request must include `Authorization: Bearer <token>`
- Tokens are compared with `secrets.compare_digest` (timing-safe)
- Invalid tokens return `401 Unauthorized` (RFC 9457 Problem Details)

### Example

```bash
curl -H "Authorization: Bearer token1" http://localhost:8080/notes
```

## API Key

### Enable

```dotenv
API_KEY_ENABLED=true
API_KEYS=["key1","key2"]
```

### Behaviour

- Every request must include `X-Api-Key: <key>`
- Invalid keys return `401 Unauthorized`

### Example

```bash
curl -H "X-Api-Key: key1" http://localhost:8080/notes
```

## Using both at once

When both `BEARER_TOKEN_ENABLED` and `API_KEY_ENABLED` are set, requests must pass both checks. In practice you would choose one or the other.

## Disabling auth in tests

```python
from nene2.config import AppSettings
from fastapi.testclient import TestClient
from example.app import create_app

client = TestClient(create_app(AppSettings(bearer_token_enabled=False)))
```

## Custom TokenVerifier (e.g. JWT)

Implement `TokenVerifierProtocol` and raise `TokenVerificationException` on failure.

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

Pass your verifier directly to `BearerTokenMiddleware`.

## Loading tokens from environment variables

Use `LocalTokenVerifier.from_env()` to avoid writing the split-and-strip boilerplate every time:

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

An unset or empty variable produces an empty allowlist — all requests are denied.

## Excluding paths from authentication

Use `exclude_paths` to bypass auth for health checks and API docs:

```python
app.add_middleware(
    BearerTokenMiddleware,
    verifier=LocalTokenVerifier.from_env("BEARER_TOKENS"),
    exclude_paths=["/docs", "/openapi.json", "/redoc", "/health"],
)
```

`ApiKeyAuthMiddleware` supports the same parameter.

## MCP server — fail fast on missing token

When an MCP server calls a Bearer-protected API via `HttpxMcpClient`, validate the token
at startup rather than discovering a missing token at call time:

```python
import os
from nene2.mcp.http_client import HttpxMcpClient

token = os.getenv("MCP_BEARER_TOKEN")
if not token:
    raise RuntimeError("MCP_BEARER_TOKEN is not set — cannot call the authenticated API.")
client = HttpxMcpClient(token)
```

## Custom TokenIssuer (e.g. JWT)

Implement `TokenIssuerProtocol` to issue tokens (e.g. for a login endpoint).

```python
from nene2.auth import TokenIssuerProtocol
import jwt

class JwtTokenIssuer:
    def __init__(self, secret: str) -> None:
        self._secret = secret

    def issue(self, claims: dict[str, object]) -> str:
        return jwt.encode(claims, self._secret, algorithm="HS256")
```
