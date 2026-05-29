# Configurar autenticação

O nene2-python suporta autenticação por Bearer Token e API Key, ambas implementadas como middleware
e habilitadas via variáveis de ambiente.

## Bearer Token

### Habilitar

Adicione ao seu arquivo `.env`:

```dotenv
BEARER_TOKEN_ENABLED=true
BEARER_TOKENS=["token1","token2","token3"]
```

### Comportamento

- Toda requisição deve incluir `Authorization: Bearer <token>`
- Os tokens são comparados com `secrets.compare_digest` (seguro contra timing attacks)
- Tokens inválidos retornam `401 Unauthorized` (Problem Details RFC 9457)

### Exemplo

```bash
curl -H "Authorization: Bearer token1" http://localhost:8080/notes
```

## API Key

### Habilitar

```dotenv
API_KEY_ENABLED=true
API_KEYS=["key1","key2"]
```

### Comportamento

- Toda requisição deve incluir `X-Api-Key: <key>`
- Chaves inválidas retornam `401 Unauthorized`

### Exemplo

```bash
curl -H "X-Api-Key: key1" http://localhost:8080/notes
```

## Usando ambos ao mesmo tempo (condição AND)

Quando ambos os middlewares são adicionados via `add_middleware`, as requisições precisam passar
**pelas duas** verificações (condição AND). Um Bearer token sozinho ou uma API key sozinha
resultarão em 401.

## Autenticação alternativa (Bearer Token OU API Key)

Se quiser aceitar **qualquer um** — Bearer token ou API key, o que estiver presente — os
middlewares embutidos não conseguem expressar isso. Implemente um middleware customizado que
reutilize os verificadores existentes:

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

## Desabilitando auth nos testes

```python
from nene2.config import AppSettings
from fastapi.testclient import TestClient
from example.app import create_app

client = TestClient(create_app(AppSettings(bearer_token_enabled=False)))
```

## TokenVerifier customizado (ex: JWT)

Implemente `TokenVerifierProtocol` e lance `TokenVerificationException` em caso de falha.

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

Passe seu verificador diretamente para o `BearerTokenMiddleware`.

## Carregando tokens de variáveis de ambiente

Use `LocalTokenVerifier.from_env()` para evitar o boilerplate de split e strip toda vez:

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

Uma variável não definida ou vazia produz uma allowlist vazia — todas as requisições são negadas.

## Excluindo caminhos da autenticação

Use `exclude_paths` para ignorar auth em health checks e API docs:

```python
app.add_middleware(
    BearerTokenMiddleware,
    verifier=LocalTokenVerifier.from_env("BEARER_TOKENS"),
    exclude_paths=["/docs", "/openapi.json", "/redoc", "/health"],
)
```

O `ApiKeyAuthMiddleware` suporta o mesmo parâmetro.

## Servidor MCP — falhe rápido em token ausente

Quando um servidor MCP chama uma API protegida por Bearer via `HttpxMcpClient`, valide o token
na inicialização em vez de descobrir um token ausente em tempo de chamada:

```python
import os
from nene2.mcp.http_client import HttpxMcpClient

token = os.getenv("MCP_BEARER_TOKEN")
if not token:
    raise RuntimeError("MCP_BEARER_TOKEN is not set — cannot call the authenticated API.")
client = HttpxMcpClient(token)
```

## TokenIssuer customizado (ex: JWT)

Implemente `TokenIssuerProtocol` para emitir tokens (ex: para um endpoint de login).

```python
from nene2.auth import TokenIssuerProtocol
import jwt

class JwtTokenIssuer:
    def __init__(self, secret: str) -> None:
        self._secret = secret

    def issue(self, claims: dict[str, object]) -> str:
        return jwt.encode(claims, self._secret, algorithm="HS256")
```
