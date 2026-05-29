# Ajouter un nouveau domaine

Une checklist pour ajouter un nouveau domaine en suivant le même schéma que Note, Tag et Comment.

## Checklist

### 1. Créer le package du domaine

```bash
mkdir -p src/example/<domain>
touch src/example/<domain>/__init__.py
```

### 2. Créer chaque fichier

| Fichier | Contenu |
|---|---|
| `entity.py` | Entité sous forme de `@dataclass(frozen=True, slots=True)` |
| `repository.py` | `XxxRepositoryInterface(ABC)` + `InMemoryXxxRepository` |
| `exceptions.py` | `XxxNotFoundException` + `XxxNotFoundExceptionHandler` |
| `use_case.py` | 5 UseCases (List / Get / Create / Update / Delete) + DTOs Input/Output |
| `handler.py` | `make_xxx_router()` — parse → use-case → response |
| `sqlalchemy_repository.py` | Implémentation du backend SQL |

### 3. Ajouter la table dans schema.py

Ajoutez un appel `CREATE TABLE` à `ensure_schema()` dans `src/example/schema.py`.

```python
executor.write(
    "CREATE TABLE IF NOT EXISTS your_domain ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "name TEXT NOT NULL,"
    "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
    ")"
)
```

### 4. Câbler dans app.py

Mettez à jour `_build_repositories()` et `create_app()` dans `src/example/app.py`.

```python
# Ajouter au tuple de retour de _build_repositories()
your_repo = SqlAlchemyYourRepository(executor)

# Enregistrer le router dans create_app()
app.include_router(make_your_router(
    list_use_case=ListYourUseCase(your_repo),
    ...
))
```

### 5. Écrire les tests

```
tests/example/<domain>/
  __init__.py
  test_<domain>_use_case.py     # Tests unitaires UseCase (sans DB)
  test_<domain>_repository.py   # Tests de contrat du repository (InMemory + SQLAlchemy)
  test_<domain>_http.py         # Tests d'intégration HTTP (TestClient)
```

### 6. Enregistrer les outils MCP (optionnel)

Ajoutez les enregistrements de UseCase à `create_mcp_server()` dans `src/example/mcp.py`.

### 7. Passer toutes les vérifications

```bash
uv run pytest && \
uv run mypy src/ && \
uv run ruff check src/ tests/ && \
uv run ruff format --check src/ tests/
```

## Conventions de nommage

| Cible | Convention | Exemple |
|---|---|---|
| Classe d'entité | PascalCase | `Note`, `Tag`, `Comment` |
| DTO d'entrée UseCase | `XxxInput` | `CreateNoteInput` |
| Exception | `XxxNotFoundException` | `NoteNotFoundException` |
| Factory de handler | `make_xxx_router()` | `make_note_router()` |

## Implémentations de référence

- `src/example/note/` — domaine CRUD basique
- `src/example/comment/` — domaine imbriqué avec clé étrangère (`note_id`)
