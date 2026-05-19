# Field Trial 10 — inventory: MySQL アダプター DX 検証

## Date

2026-05-20

## Baseline

- nene2-python v1.2.0（PyPI 経由）
- Python 3.14（uv managed）
- プロジェクト: **inventory** — 在庫管理 API
- エンティティ: `Product(id, name, price, stock, created_at)`
- HTTP API: ポート 8110（FastAPI + MySQL 8）
- DB: MySQL 8.0（Docker Compose）

## Goal

FT1〜FT9 はすべて SQLite を使用。MySQL 8 で初めて以下を検証：

1. Docker Compose で MySQL 8 を立ち上げる手順
2. `SqlAlchemyQueryExecutor` / `SqlAlchemyTransactionManager` の MySQL 上での動作
3. `parse_db_datetime()` が MySQL の `datetime` オブジェクトを正しく処理するか
4. SQLite との挙動差（`CURRENT_TIMESTAMP` 型、`RETURNING` 句）

---

## Steps Taken

### 1. Docker Compose で MySQL 8 を起動

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: inventory
      MYSQL_USER: appuser
      MYSQL_PASSWORD: apppass
    ports:
      - "3310:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-uappuser", "-papppass"]
      interval: 5s
      timeout: 5s
      retries: 10
```

`depends_on: condition: service_healthy` でアプリが MySQL の起動完了後に起動する構成。

### 2. 接続文字列と依存

```python
url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
engine = create_engine(url, pool_pre_ping=True)
```

`pymysql` + `cryptography` を追加（MySQL 8 の認証プラグイン `caching_sha2_password` 対応に必要）。

### 3. `CURRENT_TIMESTAMP` の型差異の確認

| DB | `CURRENT_TIMESTAMP` の Python 型 | `parse_db_datetime()` の結果 |
|----|----------------------------------|------------------------------|
| SQLite | `str` (`"2026-05-20 12:34:56"`) | ✓ UTC-aware datetime |
| MySQL | `datetime` (naive, server timezone) | ✓ UTC-aware datetime |

MySQL は `datetime` オブジェクトを返すが naive（tzinfo なし）。
`parse_db_datetime()` が `isinstance(value, datetime)` で分岐して `.replace(tzinfo=UTC)` を付与するため、
SQLite と同一の出力が得られることを確認。

### 4. SELECT-after-INSERT の動作確認

`RETURNING` 句は MySQL 8.0 でサポートされていない（PostgreSQL にはある）。
FT8 で採用した SELECT-after-INSERT パターンがそのまま動作：

```python
new_id = executor.write("INSERT INTO products ...", {...})
row = executor.fetch_one("SELECT ... WHERE id = :id", {"id": new_id})
```

`executor.write()` の戻り値 (`lastrowid`) が MySQL でも正しく返ることを確認。

---

## Friction Points

### FT10-1: `cryptography` が暗黙の依存として必要（ドキュメントなし）

- **摩擦**: `pymysql` を追加しただけでは MySQL 8 の `caching_sha2_password` 認証が失敗する
  ```
  OperationalError: Authentication plugin 'caching_sha2_password' is not supported
  ```
- `cryptography` パッケージを別途追加する必要があるが、エラーメッセージが分かりにくい
- **深刻度**: MEDIUM（初見では原因が pymysql の依存問題と気づきにくい）
- **解決策**: how-to ガイドに `cryptography` を必須依存として明記（ドキュメント対応）

### FT10-2: `PaginationResponse[T].to_dict()` が items を直列化しない

- **摩擦**: `PaginationResponse[ProductOutput].to_dict()` の `items` フィールドが
  `ProductOutput` dataclass インスタンスのまま返る → `json.dumps` が失敗
  ```
  TypeError: Object of type ProductOutput is not JSON serializable
  ```
- `slots=True` の dataclass は `__dict__` を持たないため `JSONResponse(result.__dict__)` も使えない
- **回避策**: ハンドラーで `[dataclasses.asdict(item) for item in result.items]` に変換
  ```python
  return JSONResponse({
      "items": [dataclasses.asdict(item) for item in result.items],
      "total": result.total,
      "limit": result.limit,
      "offset": result.offset,
  })
  ```
- **深刻度**: HIGH（LIST エンドポイントを書くたびに同じ回避策が必要）
- **解決策候補**: `PaginationResponse.to_dict()` が dataclass items を自動変換する、
  または `to_json_dict()` メソッドを追加する

### FT10-3: `ValidationError` の `code` 引数がドキュメントに不足

- **摩擦**: `ValidationError("field", "message")` → `TypeError: missing 1 required argument: 'code'`
- FT1〜FT9 の既存プロジェクトのコードを参考に 2 引数で書くと失敗する
- **深刻度**: MEDIUM（他のFTのコードがすべて3引数になっていれば問題ない）
- **解決策**: how-to ガイドのサンプルコードに `code` 引数を必ず含める

### FT10-4: `DatabaseHealthCheck(executor)` vs `DatabaseHealthCheck(engine)` が紛らわしい

- **摩擦**: `DatabaseHealthCheck` のコンストラクタは `executor` を受け取るが、
  `create_engine()` の直後に書くと `engine` を渡してしまいやすい
  ```python
  engine = create_engine(url)
  executor = SqlAlchemyQueryExecutor(engine)
  # 間違い: DatabaseHealthCheck(engine)  ← AttributeError: 'Engine' has no 'fetch_one'
  # 正しい: DatabaseHealthCheck(executor)
  ```
- **深刻度**: LOW（エラーメッセージから原因は特定できる）
- **解決策**: ドキュメントの使用例を正確に記述する

### FT10-5: `PaginationQueryParser` を FastAPI のパラメータ型として使えない

- **摩擦**: `def list_products(pagination: PaginationQueryParser)` と書くと
  `FastAPIError: Invalid args for response field` が発生
- `PaginationQueryParser` は Pydantic モデルではないため、FastAPI の Depends として使えない
- **回避策**: `request: Request` を受け取り `PaginationQueryParser.parse(request)` を呼ぶ
- **深刻度**: MEDIUM（直感的な書き方が失敗する）
- **解決策候補**: `PaginationQueryParser` を `Depends` 互換にする、または
  `Annotated[PaginationQueryParser, Depends(PaginationQueryParser.parse)]` パターンを提供

---

## Summary

| ID      | 摩擦                                                  | 深刻度 | 解決策                                                    |
|---------|-------------------------------------------------------|--------|-----------------------------------------------------------|
| FT10-1  | `cryptography` が暗黙依存（MySQL 8 認証失敗）         | MEDIUM | how-to ガイドに記載                                       |
| FT10-2  | `PaginationResponse.to_dict()` が items を直列化しない | HIGH   | `to_dict()` に dataclass 自動変換を追加                  |
| FT10-3  | `ValidationError` の `code` 引数がドキュメント不足    | MEDIUM | how-to サンプルコードを修正                               |
| FT10-4  | `DatabaseHealthCheck(executor)` vs `engine)` が紛らわしい | LOW | ドキュメント修正                                          |
| FT10-5  | `PaginationQueryParser` が FastAPI パラメータ型不可   | MEDIUM | `Depends` 互換パターンを提供                              |

**MySQL 固有の問題は FT10-1 のみ**。他は SQLite でも同様に起きる問題（FT1〜9 でたまたま発覚しなかった）。
`parse_db_datetime()` は MySQL の naive datetime を期待通り UTC-aware に変換できた。

FT11 候補:
- **FT10-2 の修正**: `PaginationResponse.to_dict()` dataclass 自動変換
- **FT10-5 の修正**: `PaginationQueryParser` を `Depends` 互換に
- **PostgreSQL アダプター**: `RETURNING` 句が使えるかを検証
- **`BearerTokenMiddleware` + `HttpxMcpClient`**: 認証付き API を MCP から呼ぶ
