# 配置身份验证

nene2-python 支持 Bearer Token 和 API Key 两种身份验证方式，均以 middleware 形式实现，并通过环境变量启用。

## Bearer Token

### 启用

在 `.env` 文件中添加：

```dotenv
BEARER_TOKEN_ENABLED=true
BEARER_TOKENS=["token1","token2","token3"]
```

### 行为

- 每个请求必须包含 `Authorization: Bearer <token>`
- Token 使用 `secrets.compare_digest` 进行比较（防时序攻击）
- 无效 Token 返回 `401 Unauthorized`（RFC 9457 Problem Details）

### 示例

```bash
curl -H "Authorization: Bearer token1" http://localhost:8080/notes
```

## API Key

### 启用

```dotenv
API_KEY_ENABLED=true
API_KEYS=["key1","key2"]
```

### 行为

- 每个请求必须包含 `X-Api-Key: <key>`
- 无效 Key 返回 `401 Unauthorized`

### 示例

```bash
curl -H "X-Api-Key: key1" http://localhost:8080/notes
```

## 同时使用两种方式（AND 条件）

当两个 middleware 都通过 `add_middleware` 添加时，请求必须同时通过**两项**检查（AND 条件）。单独的 Bearer token 或单独的 API key 都会返回 401。

## 二选一认证（Bearer Token 或 API Key）

如果您希望接受 Bearer token **或** API key 之一，内置 middleware 无法表达这种逻辑。请实现一个自定义 middleware，复用现有的验证器：

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

## 在测试中禁用认证

```python
from nene2.config import AppSettings
from fastapi.testclient import TestClient
from example.app import create_app

client = TestClient(create_app(AppSettings(bearer_token_enabled=False)))
```

## 自定义 TokenVerifier（例如 JWT）

实现 `TokenVerifierProtocol`，验证失败时抛出 `TokenVerificationException`。

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

将您的 verifier 直接传入 `BearerTokenMiddleware`。

## 从环境变量加载 Token

使用 `LocalTokenVerifier.from_env()` 避免每次手写拆分和去空格的样板代码：

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

未设置或为空的变量会产生空允许列表 — 所有请求将被拒绝。

## 从认证中排除路径

使用 `exclude_paths` 对健康检查和 API 文档跳过认证：

```python
app.add_middleware(
    BearerTokenMiddleware,
    verifier=LocalTokenVerifier.from_env("BEARER_TOKENS"),
    exclude_paths=["/docs", "/openapi.json", "/redoc", "/health"],
)
```

`ApiKeyAuthMiddleware` 支持相同的参数。

## MCP 服务器 — 在缺少 Token 时快速失败

当 MCP 服务器通过 `HttpxMcpClient` 调用 Bearer 保护的 API 时，应在启动时验证 Token，而不是在调用时才发现 Token 缺失：

```python
import os
from nene2.mcp.http_client import HttpxMcpClient

token = os.getenv("MCP_BEARER_TOKEN")
if not token:
    raise RuntimeError("MCP_BEARER_TOKEN is not set — cannot call the authenticated API.")
client = HttpxMcpClient(token)
```

## 自定义 TokenIssuer（例如 JWT）

实现 `TokenIssuerProtocol` 来签发 Token（例如用于登录 endpoint）。

```python
from nene2.auth import TokenIssuerProtocol
import jwt

class JwtTokenIssuer:
    def __init__(self, secret: str) -> None:
        self._secret = secret

    def issue(self, claims: dict[str, object]) -> str:
        return jwt.encode(claims, self._secret, algorithm="HS256")
```
