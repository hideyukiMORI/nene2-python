# 操作指南：自定义认证 middleware 与 request.state

在自定义 middleware 中将认证/授权信息存储到 `request.state`，并在 handler 中通过 `Depends()` 取回的模式。

---

## 1. 定义 AuthUser dataclass

定义一个表示已认证用户的不可变 dataclass。

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AuthUser:
    user_id: str
    roles: list[str]
```

---

## 2. 在 JWT middleware 中存储到 request.state

继承 `BaseHTTPMiddleware` 实现自定义 JWT 验证，并将 `AuthUser` 存储到 `request.state.user`。

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

## 3. 通过 Depends 工厂函数获取 AuthUser

定义一个读取 `request.state.user` 中 `AuthUser` 的 Depends 工厂函数。

```python
from fastapi import Request

def get_current_user(request: Request) -> AuthUser:
    user: AuthUser = request.state.user  # type: ignore[attr-defined]  # reason: always set by JwtAuthMiddleware
    return user
```

为何需要 `type: ignore[attr-defined]`：`request.state` 是一个 `starlette.datastructures.State` 对象，其属性是动态的，mypy 无法看到 `user` 属性。由于 middleware 保证该属性始终被设置，这里是安全的。

---

## 4. 基于角色的访问控制

定义如 `require_admin()` 这样的角色检查 Depends，并应用到 endpoint 上。

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

## 5. 何时使用此方案 vs. BearerTokenMiddleware

| 模式 | 使用方式 | 存储到 `request.state` |
|---|---|---|
| `BearerTokenMiddleware` + `make_require_auth()` | 验证/获取 Token 字符串 | 否（通过 Depends） |
| 自定义 `JwtAuthMiddleware` | 验证 JWT payload，构建 AuthUser | 是（`request.state.user`） |

**适合使用自定义 middleware 的场景**：
- 需要在 handler 中使用 JWT payload（角色、claims）
- 需要在整个请求作用域内共享认证结果

**适合使用 `BearerTokenMiddleware` 的场景**：
- 只需验证 Token 的有效性
- 需要通过 `TokenVerifierProtocol` 替换验证逻辑

---

## 6. 测试模式

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
