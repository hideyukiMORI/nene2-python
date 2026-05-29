# Como fazer: middleware de auth customizado e request.state

Um padrão para armazenar informações de autenticação/autorização em `request.state` a partir de um
middleware customizado e recuperá-las nos handlers via `Depends()`.

---

## 1. Definir um dataclass AuthUser

Defina um dataclass imutável representando o usuário autenticado.

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AuthUser:
    user_id: str
    roles: list[str]
```

---

## 2. Armazenar em request.state num middleware JWT

Subclassifique `BaseHTTPMiddleware` para implementar verificação JWT customizada e armazenar um
`AuthUser` em `request.state.user`.

```python
import jwt
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

SECRET = "your-32-char-or-longer-secret-key"

class JwtAuthMiddleware(BaseHTTPMiddleware):
    EXCLUDE_PATHS = {"/health", "/login"}

    def __init__(self, app: ASGIApp, secret: str) -> None:
        super().__init__(app)
        self._secret = secret

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        token = auth[7:]
        try:
            payload = jwt.decode(token, self._secret, algorithms=["HS256"])
            request.state.user = AuthUser(
                user_id=payload["sub"],
                roles=payload.get("roles", []),
            )
        except jwt.InvalidTokenError:
            return JSONResponse({"error": "Invalid token"}, status_code=401)

        return await call_next(request)

app = FastAPI()
app.add_middleware(JwtAuthMiddleware, secret=SECRET)
```

---

## 3. Recuperar AuthUser com uma factory Depends

Defina uma factory Depends que lê o `AuthUser` de `request.state.user`.

```python
from fastapi import Request

def get_current_user(request: Request) -> AuthUser:
    user: AuthUser = request.state.user  # type: ignore[attr-defined]  # reason: always set by JwtAuthMiddleware
    return user
```

Por que `type: ignore[attr-defined]` é necessário: `request.state` é um
`starlette.datastructures.State` com atributos dinâmicos, então o mypy não consegue ver o
atributo `user`. É seguro porque o middleware garante que ele seja definido.

---

## 4. Controle de acesso baseado em roles

Defina um Depends de verificação de role como `require_admin()` e aplique-o nos endpoints.

```python
from typing import Annotated
from fastapi import Depends, HTTPException

def require_admin(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
    if "admin" not in user.roles:
        raise HTTPException(status_code=403, detail="Admin required")
    return user

@app.get("/admin/users")
def admin_list_users(
    user: Annotated[AuthUser, Depends(require_admin)],
) -> JSONResponse:
    return JSONResponse({"admin": user.user_id, "users": [...]})
```

---

## 5. Quando usar este vs. BearerTokenMiddleware

| Padrão | Como é usado | Armazena em `request.state` |
|---|---|---|
| `BearerTokenMiddleware` + `make_require_auth()` | Verificar/obter a string do token | Não (via Depends) |
| `JwtAuthMiddleware` customizado | Verificar o payload JWT, construir AuthUser | Sim (`request.state.user`) |

**Quando um middleware customizado se encaixa**:
- você quer o payload JWT (roles, claims) nos handlers
- você quer compartilhar o resultado de auth em todo o escopo da requisição

**Quando `BearerTokenMiddleware` se encaixa**:
- você só quer verificar a validade do token
- você quer trocar a lógica de verificação via `TokenVerifierProtocol`

---

## 6. Padrão de teste

```python
import jwt
from fastapi.testclient import TestClient

SECRET = "your-32-char-or-longer-secret-key"

def make_token(user_id: str, roles: list[str]) -> str:
    return jwt.encode({"sub": user_id, "roles": roles}, SECRET, algorithm="HS256")

def test_profile_with_valid_token() -> None:
    with TestClient(app) as client:
        token = make_token("alice", ["user"])
        r = client.get("/profile", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["user_id"] == "alice"
```
