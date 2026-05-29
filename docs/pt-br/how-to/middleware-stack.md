# Como fazer: configurar a pilha de middleware corretamente

## Recomendado: use `setup_middlewares()`

Em vez de alinhar chamadas `add_middleware` manualmente, use o helper fornecido pelo
framework para evitar erros de ordenação LIFO (como um 500 não receber um
`X-Request-Id`).

```python
from nene2.middleware import setup_middlewares

setup_middlewares(
    app,
    debug=cfg.app_debug,
    domain_handlers=[NoteNotFoundExceptionHandler()],
    throttle_limit=cfg.throttle_limit if cfg.throttle_enabled else None,
    max_request_bytes=cfg.max_body_size,
    cors_allowed_origins=cfg.cors_origins if cfg.cors_enabled else None,
)
```

Pilha resultante (externo → interno):

```
CORS → RequestId → SecurityHeaders → SizeLimit → Throttle → RequestLogging → ErrorHandler
```

Use o padrão de registro manual abaixo apenas quando precisar de middleware customizado.

---

## Registro manual (TL;DR)

```python
# chame add_middleware nesta ordem
app.add_middleware(ErrorHandlerMiddleware)           # mais interno
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ThrottleMiddleware, limit=100, window=60)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)              # mais externo
```

---

## Por que essa ordem

### Regra LIFO do Starlette

`app.add_middleware()` faz **o último adicionado ser o mais externo** (LIFO).

```
add_middleware(A)  →  B(A(Router))
add_middleware(B)
```

A requisição flui de externo → interno (B → A → Router), e a resposta flui
de interno → externo (Router → A → B).

### O que quebra se ErrorHandler for o mais externo

```python
# ❌ errado
app.add_middleware(RequestIdMiddleware)
app.add_middleware(ErrorHandlerMiddleware)  # mais externo
# pilha: ErrorHandler(RequestId(Router))
```

Quando um handler lança uma exceção:

1. `ErrorHandlerMiddleware.dispatch` captura a exceção
2. retorna uma **nova Response diretamente** via `problem_details_response(...)`
3. essa Response **não passa pelo** `RequestId` middleware interno
4. resultado: **o erro 500 não tem `X-Request-Id`**

Pela mesma razão, se `SecurityHeadersMiddleware` for interno, as respostas de erro
não receberão headers de segurança.

### O diagrama correto da pilha

```
RequestIdMiddleware            ← adiciona X-Request-Id a toda resposta (200–5xx)
  └─ SecurityHeadersMiddleware ← adiciona headers de segurança a toda resposta
       └─ RequestSizeLimitMiddleware ← retorna 413 diretamente (sem ErrorHandler necessário)
            └─ ThrottleMiddleware   ← retorna 429 diretamente (sem ErrorHandler necessário)
                 └─ RequestLoggingMiddleware
                      └─ ErrorHandlerMiddleware ← converte exceções do handler em 500
                           └─ Router (handlers FastAPI)
```

`RequestSizeLimitMiddleware` e `ThrottleMiddleware` retornam
`problem_details_response()` eles mesmos, então colocá-los dentro ou fora do
ErrorHandler não muda o formato 413/429. Se `X-Request-Id` é anexado
depende da posição do `RequestIdMiddleware`.

---

## Quando algum middleware não é usado

Mesmo se você omitir algum middleware, o restante segue a mesma regra de ordenação:

```python
# quando ThrottleMiddleware e RequestLoggingMiddleware são omitidos
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
```

---

## Usando ErrorHandlerMiddleware.install()

`install()` faz `add_middleware` e `add_exception_handler` juntos, mas você
ainda precisa definir a ordem em relação a outros middlewares manualmente:

```python
# chame install() primeiro (ele se torna o mais interno)
ErrorHandlerMiddleware.install(app)          # interno

# então adicione os outros middlewares
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)       # externo
```

---

## FAQ

**Q: `RequestSizeLimitMiddleware` deve ficar dentro ou fora do ErrorHandler?**

A: Funciona de ambas as formas, mas colocá-lo dentro do `RequestIdMiddleware` significa que a
resposta 413 também recebe um `X-Request-Id`. Basta seguir a ordem recomendada acima.

**Q: Onde adiciono middleware customizado?**

A: Depende da natureza do middleware:
- quer adicionar algo a toda resposta → logo antes de `RequestIdMiddleware` (externo)
- quer capturar exceções do handler → logo após `ErrorHandlerMiddleware` (interno)
- quer rejeitar requisições cedo → perto de `RequestSizeLimitMiddleware` ou `ThrottleMiddleware`
