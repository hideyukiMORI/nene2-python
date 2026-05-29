# Como fazer: configuração de CORS

Como habilitar CORS via o parâmetro `cors_allowed_origins` de `setup_middlewares()`.

---

## 1. Básico: permitir uma única origem

```python
from nene2.middleware import setup_middlewares

app = FastAPI()
setup_middlewares(app, cors_allowed_origins=["https://example.com"])
```

Se `cors_allowed_origins` for omitido (padrão `None`), o middleware de CORS não é adicionado.

---

## 2. Permitir múltiplas origens

```python
setup_middlewares(app, cors_allowed_origins=[
    "https://app.example.com",
    "https://admin.example.com",
])
```

---

## 3. Desenvolvimento: permitir localhost

```python
import os

origins = ["https://app.example.com"]
if os.getenv("APP_ENV") == "local":
    origins += ["http://localhost:3000", "http://localhost:5173"]

setup_middlewares(app, cors_allowed_origins=origins)
```

**`allow_origins=["*"]` é proibido.** Conforme a política de segurança do CLAUDE.md, uma
origem wildcard não deve ser usada — nem mesmo em desenvolvimento.

---

## 4. Permitir credenciais (cookies, header Authorization)

`setup_middlewares()` não define `allow_credentials=True` internamente. Se precisar de
credenciais, adicione o `CORSMiddleware` diretamente.

```python
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
setup_middlewares(app)  # outros middlewares (RequestId, etc.) como de costume
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Atenção**: `add_middleware` é LIFO, então adicionar `CORSMiddleware` por último o coloca
como mais externo. Chamá-lo após `setup_middlewares()` faz o CORS rodar por fora.

---

## 5. CORS e requisições preflight

Requisições `OPTIONS` (preflight) são tratadas automaticamente pelo `CORSMiddleware`. Você
não precisa definir `@app.options(...)`.

---

## 6. Verificando headers CORS nos testes

```python
def test_cors_header() -> None:
    with TestClient(app) as client:
        r = client.get("/items", headers={"Origin": "https://app.example.com"})
        assert r.headers.get("access-control-allow-origin") == "https://app.example.com"

def test_cors_not_allowed_for_unknown_origin() -> None:
    with TestClient(app) as client:
        r = client.get("/items", headers={"Origin": "https://evil.com"})
        assert "access-control-allow-origin" not in r.headers
```
