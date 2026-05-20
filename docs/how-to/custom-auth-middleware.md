# How-to: カスタム認証ミドルウェアと request.state

カスタムミドルウェアで認証・認可情報を `request.state` に格納し、ハンドラーで `Depends()` を通じて取得するパターンを説明する。

---

## 1. AuthUser dataclass の定義

認証済みユーザー情報を表す immutable dataclass を定義する。

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AuthUser:
    user_id: str
    roles: list[str]
```

---

## 2. JWT ミドルウェアで request.state に格納

`BaseHTTPMiddleware` を継承してカスタム JWT 検証を実装し、`request.state.user` に `AuthUser` を格納する。

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

## 3. Depends ファクトリで AuthUser を取得

`request.state.user` から `AuthUser` を取得する Depends ファクトリを定義する。

```python
from fastapi import Request

def get_current_user(request: Request) -> AuthUser:
    user: AuthUser = request.state.user  # type: ignore[attr-defined]  # reason: JwtAuthMiddleware で確実に設定
    return user
```

`type: ignore[attr-defined]` が必要な理由: `request.state` は `starlette.datastructures.State` で動的属性を持つため、mypy は `user` 属性を認識できない。ミドルウェアで設定済みであることが保証されているため安全。

---

## 4. ロールベースアクセス制御

`require_admin()` のようなロール確認 Depends を定義して、エンドポイントに適用する。

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

## 5. BearerTokenMiddleware との使い分け

| パターン | 使い方 | `request.state` へ格納 |
|---|---|---|
| `BearerTokenMiddleware` + `make_require_auth()` | トークン文字列の検証・取得 | しない（Depends 経由） |
| カスタム `JwtAuthMiddleware` | JWT ペイロード検証・AuthUser 構築 | する（`request.state.user`） |

**カスタムミドルウェアが向いているケース**:
- JWT のペイロード（ロール・クレーム）をハンドラーで使いたい
- 認証結果をリクエストスコープ全体で共有したい

**`BearerTokenMiddleware` が向いているケース**:
- トークンの有効性チェックだけしたい
- `TokenVerifierProtocol` で検証ロジックを差し替えたい

---

## 6. テストパターン

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
