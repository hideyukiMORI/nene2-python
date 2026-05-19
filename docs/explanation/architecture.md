# アーキテクチャ概要

## レイヤー構造

nene2-python はクリーンアーキテクチャに基づいており、依存関係は外から内へ向かいます。

```
┌─────────────────────────────────────────────┐
│  HTTP Handler (FastAPI router)              │
│  parse request → call use-case → response  │
├─────────────────────────────────────────────┤
│  UseCase                                    │
│  ビジネスロジック。HTTP・DB を知らない      │
├─────────────────────────────────────────────┤
│  RepositoryInterface (ABC)                  │
│  ドメインが必要とする操作の契約             │
├─────────────────────────────────────────────┤
│  ConcreteRepository                         │
│  SQLAlchemy / InMemory 実装                 │
└─────────────────────────────────────────────┘
```

## 各レイヤーの責務

### HTTP Handler

- **唯一の責務**: リクエストを解析し UseCase を呼び、レスポンスを返す
- Pydantic `BaseModel` でリクエストボディを検証（HTTP 境界のみ）
- ドメインロジックを持たない
- `make_xxx_router()` ファクトリ関数がルーターを返す

```python
@router.post("", status_code=201)
async def create_note(body: CreateNoteBody) -> JSONResponse:
    note = create_use_case.execute(CreateNoteInput(title=body.title, body=body.body))
    return JSONResponse({"id": note.id, "title": note.title, "body": note.body}, status_code=201)
```

### UseCase

- **唯一の責務**: ビジネスルールを実装する
- `execute(input_: XxxInput) -> XxxOutput` の単一メソッド
- `import fastapi`, `import sqlalchemy` を持たない
- 他の UseCase を呼ばない（オーケストレーションは上位層）
- `InMemoryRepository` でテスト可能

### RepositoryInterface

- ABC で契約を定義
- UseCase は Interface のみに依存する（具象クラスを知らない）
- InMemory 実装と SQLAlchemy 実装が同じ Interface を実装する

### ConcreteRepository

- SQLAlchemy Core（ORM なし）でパラメータ化クエリを実行
- `SqlAlchemyQueryExecutor` でクエリを抽象化
- テーブルスキーマは `src/example/schema.py` で一元管理

## ミドルウェアスタック

リクエストは外側から内側に向かって処理されます:

```
BearerTokenMiddleware        認証 (Bearer Token)
ApiKeyAuthMiddleware         認証 (API Key)
CORSMiddleware               CORS
ThrottleMiddleware           レートリミット
RequestSizeLimitMiddleware   ペイロードサイズ制限
RequestLoggingMiddleware     リクエストロギング
RequestIdMiddleware          リクエスト ID 付与
SecurityHeadersMiddleware    セキュリティヘッダー付与
ErrorHandlerMiddleware       例外 → RFC 9457 Problem Details 変換
```

## DI パターン

FastAPI の `Depends` は HTTP 境界のみで使用します。UseCase とリポジトリはコンストラクタインジェクションで接続します。

```python
# app.py — ワイヤリング
note_repo = SqlAlchemyNoteRepository(executor)
app.include_router(make_note_router(
    list_use_case=ListNotesUseCase(note_repo),
    create_use_case=CreateNoteUseCase(note_repo),
    ...
))
```

## ドメインパッケージ構造

```
src/example/<domain>/
  __init__.py
  entity.py              — @dataclass(frozen=True, slots=True)
  repository.py          — ABC + InMemory 実装
  exceptions.py          — XxxNotFoundException + ExceptionHandler
  use_case.py            — 5 UseCase + Input/Output DTO
  handler.py             — FastAPI router
  sqlalchemy_repository.py — SQL バックエンド
```
