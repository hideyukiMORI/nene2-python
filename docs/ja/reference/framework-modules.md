# フレームワークモジュールリファレンス

`src/nene2/` パッケージが提供するコアモジュールの一覧です。

---

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

body = PaginationResponse(items=[...], limit=20, offset=0, total=42).to_dict()
# → {"items": [...], "limit": 20, "offset": 0, "total": 42}
```

### `problem_details_response()`

RFC 9457 準拠のエラーレスポンスを生成します。

```python
from nene2.http import problem_details_response

return problem_details_response("not-found", "Not Found", 404, "Note 42 not found.")
```

### `PaginationQuery`

`PaginationQueryParser.parse()` が返すデータクラス。`limit: int` と `offset: int` を持ちます。

### `HealthCheckProtocol` / `HealthStatus`

ヘルスチェックの契約と結果型。

```python
from nene2.http import HealthCheckProtocol, HealthStatus

class MyHealthCheck:
    def check(self) -> HealthStatus:
        return HealthStatus(status="ok")
```

`HealthStatus` フィールド: `status: str`（`"ok"` または `"error"`）、`checks: dict[str, str]`。
`is_healthy` プロパティは `status == "ok"` のとき `True`。

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

> **注意**: `isinstance` はメソッドの存在のみを確認します。同期/非同期の区別は `mypy --strict` で静的に強制されます。

---

## nene2.config

### `AppSettings`

環境変数から設定を読み込む Pydantic Settings クラス。

```python
from nene2.config import AppSettings

cfg = AppSettings()                                   # 環境変数 / .env から読み込み
cfg_test = AppSettings(throttle_enabled=False)        # テスト用オーバーライド
```

詳細は [設定リファレンス](configuration.md) を参照してください。

---

## nene2.middleware

### `ErrorHandlerMiddleware`

全例外をキャッチし RFC 9457 Problem Details に変換します。
ドメイン例外ハンドラーは `DomainExceptionHandlerProtocol` を実装して登録します。

### その他のミドルウェア

| クラス | モジュール | 役割 |
|---|---|---|
| `SecurityHeadersMiddleware` | `nene2.middleware.security_headers` | セキュリティヘッダー付与 |
| `RequestIdMiddleware` | `nene2.middleware.request_id` | X-Request-ID 付与 |
| `RequestLoggingMiddleware` | `nene2.middleware.request_logging` | structlog リクエストロギング |
| `RequestSizeLimitMiddleware` | `nene2.middleware.request_size_limit` | ペイロードサイズ制限 |
| `ThrottleMiddleware` | `nene2.middleware.throttle` | 固定ウィンドウ レートリミット |

#### `add_middleware` 引数

| ミドルウェア | キーワード引数 | デフォルト |
|---|---|---|
| `ErrorHandlerMiddleware` | `debug: bool`, `domain_handlers: list[DomainExceptionHandlerProtocol] \| None` | `False`, `None` |
| `SecurityHeadersMiddleware` | *(なし)* | — |
| `RequestIdMiddleware` | *(なし)* | — |
| `RequestLoggingMiddleware` | *(なし)* | — |
| `RequestSizeLimitMiddleware` | `max_bytes: int` | `1_048_576` (1 MiB) |
| `ThrottleMiddleware` | `limit: int`, `window: int` | `60`, `60` |

`ThrottleMiddleware` には `enabled` フラグがありません。`if settings.throttle_enabled:` でラップして制御します。

#### 完全な登録順（任意ミドルウェア含む）

```python
# 登録順: 最内側から最外側へ。Starlette は逆順に実行します（最後に登録したものが最外側）。
app.add_middleware(ErrorHandlerMiddleware, debug=settings.app_debug, domain_handlers=[...])
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_body_size)
if settings.throttle_enabled:
    app.add_middleware(ThrottleMiddleware, limit=settings.throttle_limit, window=settings.throttle_window)
# Auth ミドルウェア — CORS より前に登録して CORS レイヤーの内側に配置する
if settings.bearer_token_enabled:
    app.add_middleware(BearerTokenMiddleware, verifier=LocalTokenVerifier(settings.bearer_tokens))
if settings.api_key_enabled:
    app.add_middleware(ApiKeyAuthMiddleware, verifier=LocalTokenVerifier(settings.api_keys))
# CORS は最外側に配置 — 必ず最後に登録する。
# OPTIONS preflight リクエストは Auth チェックの前に CORSMiddleware に到達しなければならない。
# CORSMiddleware を Auth より前に登録すると、Auth が最外側になり preflight が 401 になる。
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
```

> **CORS + Auth ルール**: `CORSMiddleware` は Auth ミドルウェアの*後に*登録してください。
> Starlette の逆順ルールにより「最後に登録 = 最外側」となり、CORS が Auth をラップします。
> これによりブラウザの preflight（`OPTIONS`）リクエストが認証前に処理されます。

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

### `TokenVerifierProtocol` / `TokenIssuerProtocol`

カスタム検証器・発行器の実装に使うプロトコル（JWT など）。

### `TokenVerificationException`

トークンが無効な場合にverifier から raise します。
`BearerTokenMiddleware` が自動的に `401 Unauthorized` に変換します。

---

## nene2.database

### `SqlAlchemyQueryExecutor`

SQLAlchemy Core のラッパー。パラメータ化クエリを実行します。

```python
from nene2.database import SqlAlchemyQueryExecutor

executor = SqlAlchemyQueryExecutor(engine)
rows = executor.fetch_all("SELECT * FROM notes WHERE id = :id", {"id": 1})
executor.write("INSERT INTO notes (title, body) VALUES (:t, :b)", {"t": "t", "b": "b"})
```

#### `write()` の返り値

| 操作 | 返り値 |
|---|---|
| `AUTOINCREMENT` / `SERIAL` 付き `INSERT` | `lastrowid` — 新規行の主キー（常に > 0） |
| auto-PK なし、またはマルチ行 `INSERT` | `rowcount` — 挿入行数 |
| `UPDATE` / `DELETE` | `rowcount` — 影響行数（0 は該当なし） |

INSERT 後にエンティティを再構築する場合：

```python
new_id = executor.write("INSERT INTO notes (title) VALUES (:title)", {"title": "Hello"})
return Note(id=new_id, title="Hello")
```

UPDATE / DELETE で存在しないリソースを検出する場合：

```python
affected = executor.write("UPDATE notes SET title=:title WHERE id=:id", {"title": t, "id": pk})
if affected == 0:
    raise NoteNotFoundException(pk)
```

### `SqlAlchemyTransactionManager`

トランザクションを管理します。手動の `begin/commit/rollback` より `transactional()` を推奨します。

```python
from nene2.database import SqlAlchemyTransactionManager

mgr = SqlAlchemyTransactionManager(engine)

result = mgr.transactional(
    lambda ex: ex.fetch_one("SELECT COUNT(*) AS cnt FROM notes")
)
```

#### `transactional()` とリポジトリパターンの組み合わせ（`_in_tx` パターン）

複数テーブルへの書き込みを原子的に行う UseCase では、リポジトリインターフェースに `_in_tx` サフィックスのメソッドを定義し、`transactional()` コールバックから渡された `executor` を受け取ります。

**リポジトリインターフェース:**

```python
from nene2.database import DatabaseQueryExecutorInterface
from abc import ABC, abstractmethod

class AccountRepositoryInterface(ABC):
    # 通常メソッド — self._executor を使う（自動コミット）
    @abstractmethod
    def find_by_id(self, account_id: int) -> Account | None: ...

    # _in_tx バリアント — transactional() コールバック内からのみ呼ぶ
    @abstractmethod
    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None: ...

    @abstractmethod
    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta: int
    ) -> None: ...
```

**UseCase（送金の例）:**

```python
from nene2.database import DatabaseQueryExecutorInterface, DatabaseTransactionManagerInterface

class TransferUseCase:
    def execute(self, input_: TransferInput) -> Transfer:
        def _run(executor: DatabaseQueryExecutorInterface) -> Transfer:
            source = self._accounts.find_by_id_in_tx(executor, input_.from_account_id)
            if source is None:
                raise AccountNotFoundException(input_.from_account_id)
            if source.balance_cents < input_.amount_cents:
                raise InsufficientBalanceException(...)

            self._accounts.update_balance_in_tx(executor, input_.from_account_id, -input_.amount_cents)
            self._accounts.update_balance_in_tx(executor, input_.to_account_id, input_.amount_cents)
            return self._transfers.create_in_tx(executor, ...)

        return self._tx.transactional(_run)
```

`transactional()` は内部で `engine.begin()` を使用します — コールバック内で例外が発生した場合、自動的にロールバックされます。

詳細なパターンと InMemory テスト実装は [sqlalchemy-repository.md](../how-to/sqlalchemy-repository.md) を参照してください。

### `DatabaseHealthCheck`

`HealthCheckProtocol` を実装し、DB 接続を確認して `HealthStatus` を返します。

```python
from nene2.database import DatabaseHealthCheck
from nene2.http import HealthStatus

health = DatabaseHealthCheck(engine)
status: HealthStatus = health.check()
# status.status → "ok" または "error"
# status.checks → {"db": "ok"} または {"db": "error: <message>"}
```

### `DatabaseConnectionException`

DB 接続不能時に `DatabaseHealthCheck` やリポジトリ操作から raise されます。

---

## nene2.mcp

### `LocalMcpServer`

FastMCP をラップして UseCase を MCP ツールとして登録します。

```python
from nene2.mcp import LocalMcpServer

server = LocalMcpServer("my-server", instructions="...")

@server.tool("ノート一覧を取得する。")
def list_notes(limit: int = 20, offset: int = 0) -> list[dict]: ...

server.run(transport="stdio")
```

### `HttpxMcpClient`

MCP ツールハンドラーから nene2 API を呼び出す HTTP クライアント。

```python
from nene2.mcp import HttpxMcpClient

client = HttpxMcpClient("bearer-token")
response = client.get("http://localhost:8080", "/notes")
response.is_successful()   # True
response.body              # str — 生のレスポンステキスト
response.status_code       # int
response.request_id()      # str | None — X-Request-ID ヘッダーの値
```

### `McpHttpResponse`

`HttpxMcpClient` メソッドの戻り値型。

フィールド: `status_code: int`、`headers: dict[str, str]`、`body: str`（生のレスポンステキスト）。

メソッド:
- `is_successful() -> bool`（`200 ≤ status_code < 300` のとき `True`）
- `request_id() -> str | None` — `X-Request-ID` レスポンスヘッダーの値を返す（なければ `None`）

### `McpHttpClientProtocol`

カスタム MCP HTTP クライアントの構造的契約。`get()`・`post()`・`put()`・`delete()` で `McpHttpResponse` を返し、`has_authentication() -> bool` を実装します。

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
