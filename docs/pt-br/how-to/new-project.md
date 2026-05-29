# Começar um novo projeto com nene2

Este guia mostra como criar um novo projeto que usa o nene2 como dependência — não um clone deste repositório.

## Pré-requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) instalado

## 1. Inicializar o projeto

```bash
mkdir my-api && cd my-api
uv init --name my-api --no-workspace
```

## 2. Adicionar nene2 como dependência

Instalar a partir do GitHub (estável, versão mais recente):

```bash
uv add "nene2-python @ git+https://github.com/hideyukiMORI/nene2-python.git"
```

## 3. Layout do projeto

Organize seu código sob `src/`:

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
      sqlalchemy_repository.py   # opcional — pule para InMemory apenas
    app.py                       # factory da aplicação FastAPI
  .env
  pyproject.toml
```

## 4. Criar um domínio

Siga o tutorial [Implementar um novo domínio](../tutorials/first-domain.md).
Use `InMemoryXxxRepository` durante o desenvolvimento — conecte `SqlAlchemyXxxRepository` quando precisar de persistência.

## 5. Montar a aplicação

Crie `src/app.py`:

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

    # O middleware é aplicado em ordem inversa ao registro.
    # Adicione o mais interno (error handler) primeiro, o mais externo (throttle) por último.
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
    # Middleware de auth — registrado antes do CORS para ficar dentro da camada CORS.
    if settings.bearer_token_enabled:
        app.add_middleware(BearerTokenMiddleware, verifier=LocalTokenVerifier(settings.bearer_tokens))
    if settings.api_key_enabled:
        app.add_middleware(ApiKeyAuthMiddleware, verifier=LocalTokenVerifier(settings.api_keys))
    # CORS deve ser a camada mais externa — registre por último.
    # Requisições de preflight OPTIONS devem chegar ao CORSMiddleware antes de qualquer verificação de auth.
    # Se CORSMiddleware for registrado antes do middleware de auth, a camada de auth se torna
    # mais externa e retorna 401 no preflight, quebrando CORS para todos os navegadores.
    if settings.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )

    # Converta erros de validação do BaseModel Pydantic para RFC 9457 Problem Details
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)  # type: ignore[arg-type]

    return app


app = create_app()
```

> **Nota sobre ordenação de middleware:** O `add_middleware` do Starlette aplica middleware em ordem inversa ao registro — o último registrado se torna a camada mais externa. Registre `ErrorHandlerMiddleware` primeiro para que envolva tudo e capture todas as exceções não tratadas.

> **Regra CORS + Auth**: Sempre registre `CORSMiddleware` *após* qualquer middleware de auth. Na ordem inversa do Starlette, "último registrado = mais externo" significa que CORS envolve auth, então requisições de preflight do navegador (`OPTIONS`) são tratadas antes da autenticação.

## 6. Executar o servidor de desenvolvimento

```bash
PYTHONPATH=src uv run uvicorn app:app --reload --port 8080
```

Abra `http://localhost:8080/docs` para o Swagger UI.

## 7. Executar os testes

```bash
PYTHONPATH=src uv run pytest
```

Use `AppSettings(throttle_enabled=False)` em fixtures de teste para desabilitar rate limiting:

```python
from fastapi.testclient import TestClient
from nene2.config import AppSettings
from app import create_app

client = TestClient(create_app(AppSettings(throttle_enabled=False)))
```
