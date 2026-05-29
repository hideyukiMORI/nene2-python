# Guide pratique : middleware d'auth personnalisé et request.state

Un schéma pour stocker les informations d'authentification/autorisation dans `request.state`
depuis un middleware personnalisé et les récupérer dans les handlers via `Depends()`.

---

## 1. Définir un dataclass AuthUser

Définissez un dataclass immuable représentant l'utilisateur authentifié.

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AuthUser:
    user_id: str
    roles: list[str]
```

---

## 2. Stocker dans request.state depuis un middleware JWT

Sous-classez `BaseHTTPMiddleware` pour implémenter une vérification JWT personnalisée et stocker
un `AuthUser` dans `request.state.user`.

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

## 3. Récupérer AuthUser avec une factory Depends

Définissez une factory Depends qui lit l'`AuthUser` depuis `request.state.user`.

```python
from fastapi import Request

def get_current_user(request: Request) -> AuthUser:
    user: AuthUser = request.state.user  # type: ignore[attr-defined]  # reason: always set by JwtAuthMiddleware
    return user
```

Pourquoi `type: ignore[attr-defined]` est nécessaire : `request.state` est un
`starlette.datastructures.State` avec des attributs dynamiques, donc mypy ne peut pas voir
l'attribut `user`. C'est sûr car le middleware garantit qu'il est défini.

---

## 4. Contrôle d'accès basé sur les rôles

Définissez un Depends de vérification de rôle comme `require_admin()` et appliquez-le aux endpoints.

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

## 5. Quand utiliser ceci vs. BearerTokenMiddleware

| Schéma | Comment c'est utilisé | Stocke dans `request.state` |
|---|---|---|
| `BearerTokenMiddleware` + `make_require_auth()` | Vérifier/obtenir la chaîne du token | Non (via Depends) |
| `JwtAuthMiddleware` personnalisé | Vérifier le payload JWT, construire AuthUser | Oui (`request.state.user`) |

**Quand un middleware personnalisé convient** :
- vous voulez le payload JWT (rôles, claims) dans les handlers
- vous voulez partager le résultat de l'auth sur toute la portée de la requête

**Quand `BearerTokenMiddleware` convient** :
- vous voulez seulement vérifier la validité du token
- vous voulez échanger la logique de vérification via `TokenVerifierProtocol`

---

## 6. Schéma de test

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
