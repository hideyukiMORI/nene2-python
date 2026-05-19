# フレームワークモジュールリファレンス

`src/nene2/` パッケージが提供するコアモジュールの一覧です。

## nene2.http

### `PaginationQueryParser`

クエリパラメータ `limit` と `offset` を解析します。

```python
from nene2.http import PaginationQueryParser

pagination = PaginationQueryParser.parse(request)
# pagination.limit  → int (max 100, default 20)
# pagination.offset → int (default 0)
```

### `PaginationResponse`

ページネーションレスポンスの構造。

```python
from nene2.http import PaginationResponse

response = PaginationResponse(items=[...], limit=20, offset=0, total=42)
return JSONResponse(response.to_dict())
# → {"items": [...], "limit": 20, "offset": 0, "total": 42}
```

### `problem_details_response()`

RFC 9457 準拠のエラーレスポンスを生成します。

```python
from nene2.http import problem_details_response

return problem_details_response(
    problem_type="not-found",
    title="Not Found",
    status=404,
    detail="Note with ID 42 was not found.",
)
```

---

## nene2.use_case

### `UseCaseProtocol[I, O]`

同期 UseCase の構造的型契約。

```python
from nene2.use_case import UseCaseProtocol

class MyUseCase:
    def execute(self, input_: MyInput) -> MyOutput: ...

assert isinstance(MyUseCase(), UseCaseProtocol)
```

### `AsyncUseCaseProtocol[I, O]`

非同期 UseCase の構造的型契約。

```python
from nene2.use_case import AsyncUseCaseProtocol

class MyAsyncUseCase:
    async def execute(self, input_: MyInput) -> MyOutput: ...

assert isinstance(MyAsyncUseCase(), AsyncUseCaseProtocol)
```

---

## nene2.config

### `AppSettings`

環境変数から設定を読み込む Pydantic Settings クラス。
詳細は [設定リファレンス](configuration.md) を参照してください。

```python
from nene2.config import AppSettings

cfg = AppSettings()  # 環境変数 / .env から読み込み
cfg_test = AppSettings(throttle_enabled=False)  # テスト用オーバーライド
```

---

## nene2.middleware

### `ErrorHandlerMiddleware`

全例外をキャッチし RFC 9457 Problem Details に変換します。
ドメイン例外ハンドラーは `DomainExceptionHandlerProtocol` を実装して登録します。

```python
from nene2.middleware import ErrorHandlerMiddleware
from nene2.middleware.domain_exception import DomainExceptionHandlerProtocol

class MyExceptionHandler:
    def handles(self, exc: Exception) -> bool:
        return isinstance(exc, MyException)
    def handle(self, exc: Exception) -> Response:
        return problem_details_response("my-error", "My Error", 400)
```

### その他のミドルウェア

| クラス | モジュール | 役割 |
|---|---|---|
| `SecurityHeadersMiddleware` | `nene2.middleware.security_headers` | セキュリティヘッダー付与 |
| `RequestIdMiddleware` | `nene2.middleware.request_id` | X-Request-ID 付与 |
| `RequestLoggingMiddleware` | `nene2.middleware.request_logging` | structlog リクエストロギング |
| `RequestSizeLimitMiddleware` | `nene2.middleware.request_size_limit` | ペイロードサイズ制限 |
| `ThrottleMiddleware` | `nene2.middleware.throttle` | 固定ウィンドウ レートリミット |

---

## nene2.auth

### `LocalTokenVerifier`

`secrets.compare_digest` で静的トークンリストを検証します。

```python
from nene2.auth import LocalTokenVerifier

verifier = LocalTokenVerifier(["token-a", "token-b"])
verifier.verify("token-a")  # True
verifier.verify("wrong")    # False
```

### `TokenVerifierProtocol`

カスタム検証器の実装に使うプロトコル。

```python
from nene2.auth.interfaces import TokenVerifierProtocol

class JwtVerifier:
    def verify(self, token: str) -> bool: ...
```

---

## nene2.mcp

### `LocalMcpServer`

MCP サーバーを構築するラッパー。

```python
from nene2.mcp import LocalMcpServer

server = LocalMcpServer("my-server", instructions="...")

@server.tool("ノート一覧を取得する。")
def list_notes(limit: int = 20, offset: int = 0) -> list[dict]: ...

server.run(transport="stdio")  # Claude Desktop 向け
```

---

## nene2.database

### `SqlAlchemyQueryExecutor`

SQLAlchemy Core のラッパー。パラメータ化クエリを実行します。

```python
from nene2.database import SqlAlchemyQueryExecutor

executor = SqlAlchemyQueryExecutor(engine)
rows = executor.query("SELECT * FROM notes WHERE id = :id", {"id": 1})
executor.write("INSERT INTO notes (title, body) VALUES (:title, :body)", {...})
```

---

## nene2.log

### `setup_logging()`

structlog を初期化します。`app_env` に応じてレンダラーを切り替えます。

```python
from nene2.log import setup_logging

setup_logging(app_env="production")  # JSON レンダラー
setup_logging(app_env="local")       # Console レンダラー
```

---

## nene2.validation

### `ValidationException` / `ValidationError`

HTTP 入力検証失敗時に `422 Unprocessable Entity` を返す例外。

```python
from nene2.validation.exceptions import ValidationError, ValidationException

errors = [ValidationError("body", "Body must not be empty.", "required")]
raise ValidationException(errors)
```
