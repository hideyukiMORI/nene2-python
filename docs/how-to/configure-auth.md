# Configure authentication

nene2-python supports Bearer Token and API Key authentication, both implemented as middleware and enabled via environment variables.

## Bearer Token

### Enable

Add to your `.env` file:

```dotenv
BEARER_TOKEN_ENABLED=true
BEARER_TOKENS=token1,token2,token3
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
API_KEYS=key1,key2
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
from nene2.auth import TokenVerificationException
from nene2.auth.interfaces import TokenVerifierProtocol
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
