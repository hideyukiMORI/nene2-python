# Exécuter les tests

## Commandes de base

```bash
# Exécuter tous les tests avec couverture
uv run pytest

# Sortie détaillée en cas d'échec
uv run pytest --tb=short -v

# Exécuter un répertoire spécifique
uv run pytest tests/example/note/

# Générer un rapport de couverture HTML
uv run pytest --cov=src --cov-report=html
# → ouvrir htmlcov/index.html dans votre navigateur
```

## Structure des tests

```
tests/
  nene2/              Tests unitaires du cœur du framework
    use_case/         Conformité UseCaseProtocol
    auth/             Middleware et vérificateurs d'auth
    database/         Tests TransactionManager
    mcp/              Tests McpHttpClient
    middleware/       Chaque middleware en isolation
  example/
    note/             Tests du domaine Note
      test_list_notes.py           Tests unitaires UseCase
      test_note_repository.py      Tests de contrat du repository
      test_async_note_use_case.py  Tests UseCase async
    comment/
      test_comment_use_case.py     Tests unitaires UseCase (sans DB)
      test_comment_repository.py   Tests de contrat InMemory + SQLAlchemy
      test_comment_http.py         Tests d'intégration HTTP (TestClient)
```

## Types de tests

### Tests unitaires UseCase

Pas de base de données, pas de HTTP — utilisent des repositories InMemory. Les plus rapides.

```python
def test_create_note() -> None:
    repo = InMemoryNoteRepository()
    note = CreateNoteUseCase(repo).execute(CreateNoteInput(title="t", body="b"))
    assert note.title == "t"
```

### Tests de contrat de repository

`@pytest.fixture(params=["inmemory", "sqlalchemy"])` exécute les mêmes assertions contre les
deux implémentations.

```python
@pytest.fixture(params=["inmemory", "sqlalchemy"])
def repo(request): ...

def test_save_and_find(repo) -> None:
    note = repo.save("title", "body")
    assert repo.find_by_id(note.id) == note
```

### Tests d'intégration HTTP

Utilisent le `TestClient` de FastAPI. Teste toute la pile de HTTP jusqu'au repository.

```python
def test_create_note_returns_201() -> None:
    client = TestClient(create_app(AppSettings(throttle_enabled=False)))
    response = client.post("/notes", json={"title": "t", "body": "b"})
    assert response.status_code == 201
```

### Tests async

`asyncio_mode = "auto"` est défini dans `pyproject.toml`, donc `async def test_*` fonctionne directement.

```python
async def test_async_list_notes() -> None:
    repo = InMemoryNoteRepository()
    result = await AsyncListNotesUseCase(repo).execute(ListNotesInput(limit=10, offset=0))
    assert result.total == 0
```

## SQLite en mémoire pour les tests d'intégration

Quand vous utilisez `SqlAlchemyQueryExecutor` ou `SqlAlchemyTransactionManager` avec une base
de données SQLite en mémoire, passez toujours `poolclass=StaticPool`. Sans cela, SQLAlchemy
peut ouvrir une nouvelle connexion physique qui voit une base de données vide.

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

`StaticPool` garantit que toutes les connexions logiques partagent la même connexion SQLite
sous-jacente, de sorte que les tables créées dans une opération sont visibles pour la suivante.

**Application des clés étrangères SQLite** : SQLite désactive les contraintes de clé étrangère
par défaut. Activez-les avec `PRAGMA foreign_keys=ON` juste après la création du moteur :

```python
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("PRAGMA foreign_keys=ON"))
```

Avec `StaticPool`, un seul appel s'applique à la connexion partagée unique, donc toutes les
opérations suivantes voient les contraintes FK appliquées.

## Capturer les sorties structlog avec caplog

Appelez `configure_for_testing()` au niveau du module dans `conftest.py` pour router structlog
via le pont de journalisation stdlib afin que la fixture `caplog` de pytest puisse le capturer.

```python
# conftest.py
from nene2.log import configure_for_testing
configure_for_testing()
```

Puis faites des assertions sur les chaînes de messages dans les tests :

```python
def test_handler_logs(caplog: pytest.LogCaptureFixture) -> None:
    client = TestClient(create_app())
    client.post("/api/echo", json={"message": "hello"})
    assert any("processing echo" in r.message for r in caplog.records)
```

**Note** : `caplog.records` retourne des objets stdlib `LogRecord`. Les champs liés avec
`structlog.contextvars.bind_contextvars()` (comme `request_id`) ne sont pas directement
accessibles comme `record.request_id` — ils apparaissent dans la chaîne de message formatée.

## Méthodes HTTP du TestClient et paramètre json

Les méthodes `.get()`, `.post()`, `.put()`, `.patch()` de `TestClient` acceptent le paramètre
`json=`, mais `.delete()` ne l'accepte pas (`TypeError`). Pour DELETE avec un corps, utilisez
`.request()`.

```python
# ✅ GET/POST/PUT/PATCH acceptent json=
r = client.post("/items", json={"name": "Alice"})
r = client.put("/items/1", json={"name": "Bob"})

# ❌ DELETE n'accepte pas json=
r = client.delete("/items/bulk", json={"ids": [1, 2]})  # TypeError

# ✅ DELETE + corps : utiliser request()
r = client.request("DELETE", "/items/bulk", json={"ids": [1, 2]})
```

**Note de conception** : Avoir un corps de requête dans DELETE est "déconseillé" par la RFC 9110
(certains serveurs l'ignorent). Pour la suppression en masse, envisagez aussi le schéma
`POST /items/bulk-delete`.

---

## Exigences de couverture

| Périmètre | Cible |
|---|---|
| Global | ≥ 80% (enforced par CI via `pytest --cov-fail-under=80`) |
| UseCase / Domaine | ≥ 90% (enforced par CI sur `example/*/use_case.py`, `entity.py`, `async_use_case.py`) |

Base actuelle : **466 tests**, ~93% de couverture globale.

## Analyse statique

```bash
uv run mypy src/          # Vérification de types (strict)
uv run ruff check src/ tests/    # Lint
uv run ruff format --check src/ tests/  # Vérification du format
uv run pip-audit --ignore-vuln PYSEC-2025-183  # Scan des dépendances (correspond à la CI)
```

La CI s'exécute sur **Python 3.12 et 3.14** (voir `.github/workflows/ci.yml`).
