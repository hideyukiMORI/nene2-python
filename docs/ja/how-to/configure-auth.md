# 認証を設定する

nene2-python は Bearer Token 認証と API Key 認証の 2 種類をサポートしています。
どちらもミドルウェアとして実装されており、環境変数で有効化できます。

## Bearer Token 認証

### 有効化する

`.env` ファイルに以下を追加します:

```dotenv
BEARER_TOKEN_ENABLED=true
BEARER_TOKENS=["token1","token2","token3"]
```

### 動作

- `Authorization: Bearer <token>` ヘッダーが必須になります
- トークンは `secrets.compare_digest` でタイミング安全な比較を行います
- 無効なトークンは `401 Unauthorized` を返します

### curl での利用

```bash
curl -H "Authorization: Bearer token1" http://localhost:8080/notes
```

## API Key 認証

### 有効化する

```dotenv
API_KEY_ENABLED=true
API_KEYS=["key1","key2"]
```

### 動作

- `X-Api-Key: <key>` ヘッダーが必須になります
- 無効なキーは `401 Unauthorized` を返します

### curl での利用

```bash
curl -H "X-Api-Key: key1" http://localhost:8080/notes
```

## 両方を有効化する場合

Bearer Token と API Key を同時に有効化すると、リクエストは両方の認証を通過する必要があります。
通常はどちらか一方を使います。

## テスト時に認証を無効化する

```python
from nene2.config import AppSettings
from fastapi.testclient import TestClient
from example.app import create_app

client = TestClient(create_app(AppSettings(bearer_token_enabled=False)))
```

## カスタム TokenVerifier を実装する

`TokenVerifierProtocol` を実装することで、JWT や外部サービスによる検証を追加できます。

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

`TokenVerificationException` を raise することで、`BearerTokenMiddleware` が自動的に `401 Unauthorized` を返します。

## カスタム TokenIssuer を実装する

`TokenIssuerProtocol` を実装して、JWT などのトークンを発行できます。

```python
from nene2.auth import TokenIssuerProtocol
import jwt

class JwtTokenIssuer:
    def __init__(self, secret: str) -> None:
        self._secret = secret

    def issue(self, claims: dict[str, object]) -> str:
        return jwt.encode(claims, self._secret, algorithm="HS256")
```
