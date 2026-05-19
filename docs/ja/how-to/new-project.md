# nene2 を使った新しいプロジェクトを作る

このガイドは、このリポジトリを clone するのではなく、nene2 を依存関係として使う新しいプロジェクトを作成する手順を説明します。

## 前提条件

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) がインストール済み

## 1. プロジェクトを初期化する

```bash
mkdir my-api && cd my-api
uv init --name my-api --no-workspace
```

## 2. nene2 を依存関係として追加する

GitHub からインストールします（最新の安定版）:

```bash
uv add "nene2-python @ git+https://github.com/hideyukiMORI/nene2-python.git"
```

## 3. プロジェクト構成

`src/` 以下にソースを配置します:

```
my-api/
  src/
    myapp/
      __init__.py
      entity.py
      repository.py
      exceptions.py
      use_case.py
      handler.py
      sqlalchemy_repository.py   # 任意 — InMemory のみの場合は省略可
    app.py                       # FastAPI アプリケーションファクトリ
  .env
  pyproject.toml
```

## 4. ドメインを作る

[新しいドメインを実装する](../tutorials/first-domain.md) チュートリアルに従ってください。
開発中は `InMemoryXxxRepository` を使い、永続化が必要になったら `SqlAlchemyXxxRepository` に切り替えます。

## 5. アプリケーションを配線する

`src/app.py` を作成します:

```python
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from nene2.auth import ApiKeyAuthMiddleware, BearerTokenMiddleware, LocalTokenVerifier
from nene2.config import AppSettings
from nene2.log import setup_logging
from nene2.middleware import ErrorHandlerMiddleware
from nene2.middleware.error_handler import request_validation_error_handler
from nene2.middleware.request_id import RequestIdMiddleware
from nene2.middleware.request_logging import RequestLoggingMiddleware
from nene2.middleware.request_size_limit import RequestSizeLimitMiddleware
from nene2.middleware.security_headers import SecurityHeadersMiddleware
from nene2.middleware.throttle import ThrottleMiddleware

from myapp.exceptions import MyEntityNotFoundExceptionHandler
from myapp.handler import make_my_router
from myapp.repository import InMemoryMyRepository
from myapp.use_case import CreateMyUseCase, DeleteMyUseCase, GetMyUseCase, ListMyUseCase, UpdateMyUseCase


def create_app(settings: AppSettings | None = None) -> FastAPI:
    if settings is None:
        settings = AppSettings()

    setup_logging(app_env=settings.app_env)

    app = FastAPI(title="my-api", version="0.1.0")

    repo = InMemoryMyRepository()
    app.include_router(make_my_router(
        list_use_case=ListMyUseCase(repo),
        get_use_case=GetMyUseCase(repo),
        create_use_case=CreateMyUseCase(repo),
        update_use_case=UpdateMyUseCase(repo),
        delete_use_case=DeleteMyUseCase(repo),
    ))

    # ミドルウェアは登録の逆順に適用されます。
    # 最内側（エラーハンドラー）を最初に、最外側（スロットル）を最後に登録します。
    app.add_middleware(
        ErrorHandlerMiddleware,
        debug=settings.app_debug,
        domain_handlers=[MyEntityNotFoundExceptionHandler()],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_body_size)
    if settings.throttle_enabled:
        app.add_middleware(
            ThrottleMiddleware,
            limit=settings.throttle_limit,
            window=settings.throttle_window,
        )
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

    # Pydantic BaseModel の検証エラーを RFC 9457 Problem Details に変換
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)  # type: ignore[arg-type]

    return app


app = create_app()
```

> **ミドルウェア登録順の注意:** Starlette の `add_middleware` は逆順に適用されます — 最後に登録したものが最外側のレイヤーになります。`ErrorHandlerMiddleware` を最初に登録することですべての例外をキャッチします。

> **CORS + Auth ルール**: `CORSMiddleware` は Auth ミドルウェアの*後に*必ず登録してください。Starlette の逆順ルールにより「最後に登録 = 最外側」となり、CORS が Auth をラップします。これによりブラウザの preflight（`OPTIONS`）リクエストが認証前に処理されます。

## 6. 開発サーバーを起動する

```bash
PYTHONPATH=src uv run uvicorn app:app --reload --port 8080
```

`http://localhost:8080/docs` で Swagger UI が開きます。

## 7. テストを実行する

```bash
PYTHONPATH=src uv run pytest
```

テストのフィクスチャでは `AppSettings(throttle_enabled=False)` を使ってレートリミットを無効化します:

```python
from fastapi.testclient import TestClient
from nene2.config import AppSettings
from app import create_app

client = TestClient(create_app(AppSettings(throttle_enabled=False)))
```
