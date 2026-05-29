# Guide pratique : configurer CORS

Comment activer CORS via le paramètre `cors_allowed_origins` de `setup_middlewares()`.

---

## 1. Bases : autoriser une seule origine

```python
from nene2.middleware import setup_middlewares

app = FastAPI()
setup_middlewares(app, cors_allowed_origins=["https://example.com"])
```

Si `cors_allowed_origins` est omis (par défaut `None`), le middleware CORS n'est pas ajouté.

---

## 2. Autoriser plusieurs origines

```python
setup_middlewares(app, cors_allowed_origins=[
    "https://app.example.com",
    "https://admin.example.com",
])
```

---

## 3. Développement : autoriser localhost

```python
import os

origins = ["https://app.example.com"]
if os.getenv("APP_ENV") == "local":
    origins += ["http://localhost:3000", "http://localhost:5173"]

setup_middlewares(app, cors_allowed_origins=origins)
```

**`allow_origins=["*"]` est interdit.** Conformément à la politique de sécurité de CLAUDE.md,
une origine wildcard ne doit pas être utilisée — même en développement.

---

## 4. Autoriser les credentials (cookies, en-tête Authorization)

`setup_middlewares()` ne définit pas `allow_credentials=True` en interne. Si vous avez besoin
de credentials, ajoutez `CORSMiddleware` directement.

```python
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
setup_middlewares(app)  # autres middleware (RequestId, etc.) comme d'habitude
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Note** : `add_middleware` est LIFO, donc ajouter `CORSMiddleware` en dernier le place à
l'extérieur. L'appeler après `setup_middlewares()` fait s'exécuter CORS en position externe.

---

## 5. CORS et requêtes preflight

Les requêtes `OPTIONS` (preflight) sont gérées automatiquement par `CORSMiddleware`. Vous
n'avez pas besoin de définir `@app.options(...)`.

---

## 6. Vérifier les en-têtes CORS dans les tests

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
