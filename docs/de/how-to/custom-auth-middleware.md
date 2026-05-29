# How-to: benutzerdefinierte Auth-Middleware und request.state

Ein Muster zum Speichern von Authentifizierungs-/Autorisierungsinformationen auf `request.state` aus einer benutzerdefinierten Middleware und zum Abrufen in Handlern über `Depends()`.

---

## 1. AuthUser-Dataclass definieren

Definieren Sie einen unveränderlichen Dataclass, der den authentifizierten Benutzer repräsentiert.

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AuthUser:
    user_id: str
    roles: list[str]
```

---

## 2. Auf request.state in einer JWT-Middleware speichern

Leiten Sie `BaseHTTPMiddleware` ab, um benutzerdefinierte JWT-Überprüfung zu implementieren und einen `AuthUser` auf `request.state.user` zu speichern.

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

## 3. AuthUser mit einer Depends-Factory abrufen

Definieren Sie eine Depends-Factory, die den `AuthUser` aus `request.state.user` liest.

```python
from fastapi import Request

def get_current_user(request: Request) -> AuthUser:
    user: AuthUser = request.state.user  # type: ignore[attr-defined]  # reason: always set by JwtAuthMiddleware
    return user
```

Warum `type: ignore[attr-defined]` benötigt wird: `request.state` ist ein `starlette.datastructures.State` mit dynamischen Attributen, daher kann mypy das `user`-Attribut nicht sehen. Es ist sicher, weil die Middleware garantiert, dass es gesetzt ist.

---

## 4. Rollenbasierte Zugriffskontrolle

Definieren Sie eine rollenprüfende Depends wie `require_admin()` und wenden Sie sie auf Endpunkte an.

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

## 5. Wann dieses Muster vs. BearerTokenMiddleware verwenden

| Muster | Verwendung | Speichert auf `request.state` |
|---|---|---|
| `BearerTokenMiddleware` + `make_require_auth()` | Token-String verifizieren/abrufen | Nein (über Depends) |
| Benutzerdefinierte `JwtAuthMiddleware` | JWT-Payload prüfen, AuthUser aufbauen | Ja (`request.state.user`) |

**Wann eine benutzerdefinierte Middleware passt**:
- Sie möchten den JWT-Payload (Rollen, Claims) in Handlern
- Sie möchten das Auth-Ergebnis über den gesamten Request-Scope teilen

**Wann `BearerTokenMiddleware` passt**:
- Sie möchten nur die Token-Gültigkeit prüfen
- Sie möchten die Verifizierungslogik über `TokenVerifierProtocol` austauschen

---

## 6. Testmuster

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
