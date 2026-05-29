# 使用 nene2 创建新项目

本指南带您创建一个以 nene2 为依赖的新项目，而非克隆本仓库。

## 前提条件

- Python 3.12+
- 已安装 [uv](https://docs.astral.sh/uv/)

## 1. 初始化项目

```bash
mkdir my-api && cd my-api
uv init --name my-api --no-workspace
```

## 2. 添加 nene2 为依赖

从 GitHub 安装（稳定版，最新发布）：

```bash
uv add "nene2-python @ git+https://github.com/hideyukiMORI/nene2-python.git"
```

## 3. 项目结构

将源代码组织到 `src/` 下：

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
      sqlalchemy_repository.py   # 可选 — 仅使用 InMemory 时可省略
    app.py                       # FastAPI 应用工厂
  .env
  pyproject.toml
```

## 4. 创建领域

参照 [实现新领域](../tutorials/first-domain.md) 教程。
开发阶段使用 `InMemoryXxxRepository`，需要持久化时再接入 `SqlAlchemyXxxRepository`。

## 5. 组装应用

创建 `src/app.py`：

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

    # Middleware 以注册顺序的逆序应用。
    # 先添加最内层（error handler），最后添加最外层（throttle）。
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
    # Auth middleware — 在 CORS 之前注册，使其位于 CORS 层内部。
    if settings.bearer_token_enabled:
        app.add_middleware(BearerTokenMiddleware, verifier=LocalTokenVerifier(settings.bearer_tokens))
    if settings.api_key_enabled:
        app.add_middleware(ApiKeyAuthMiddleware, verifier=LocalTokenVerifier(settings.api_keys))
    # CORS 必须是最外层 — 最后注册。
    # OPTIONS 预检请求必须在任何认证检查之前到达 CORSMiddleware。
    # 如果 CORSMiddleware 在 auth middleware 之前注册，auth 层将成为最外层，
    # 对预检请求返回 401，导致所有浏览器的 CORS 失败。
    if settings.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )

    # 将 Pydantic BaseModel 验证错误转换为 RFC 9457 Problem Details
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)  # type: ignore[arg-type]

    return app


app = create_app()
```

> **Middleware 顺序注意：** Starlette 的 `add_middleware` 以注册顺序的逆序应用 middleware — 最后注册的成为最外层。先注册 `ErrorHandlerMiddleware`，使其包裹所有其他层并捕获所有未处理异常。

> **CORS + Auth 规则**：始终在 auth middleware *之后*注册 `CORSMiddleware`。在 Starlette 的逆序中，"最后注册 = 最外层"意味着 CORS 包裹 auth，浏览器预检（`OPTIONS`）请求在认证之前得到处理。

## 6. 运行开发服务器

```bash
PYTHONPATH=src uv run uvicorn app:app --reload --port 8080
```

打开 `http://localhost:8080/docs` 查看 Swagger UI。

## 7. 运行测试

```bash
PYTHONPATH=src uv run pytest
```

在测试 fixture 中使用 `AppSettings(throttle_enabled=False)` 禁用限流：

```python
from fastapi.testclient import TestClient
from nene2.config import AppSettings
from app import create_app

client = TestClient(create_app(AppSettings(throttle_enabled=False)))
```
