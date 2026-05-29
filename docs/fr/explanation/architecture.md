# Vue d'ensemble de l'architecture

## Structure en couches

nene2-python suit la Clean Architecture. Les dépendances vont de l'extérieur vers l'intérieur.

```
┌─────────────────────────────────────────────┐
│  HTTP Handler (FastAPI router)              │
│  parse request → call use-case → response  │
├─────────────────────────────────────────────┤
│  UseCase                                    │
│  Logique métier — sans connaissance HTTP/DB │
├─────────────────────────────────────────────┤
│  RepositoryInterface (ABC)                  │
│  Contrat pour les opérations dont le domaine│
│  a besoin                                   │
├─────────────────────────────────────────────┤
│  ConcreteRepository                         │
│  Implémentations SQLAlchemy / InMemory      │
└─────────────────────────────────────────────┘
```

## Responsabilités des couches

### HTTP Handler

- **Responsabilité unique** : parser la requête, appeler un UseCase, retourner une réponse
- Utilise le `BaseModel` de Pydantic pour la validation du corps de la requête (à la frontière HTTP uniquement)
- Ne contient aucune logique de domaine
- Exposé via une fonction factory `make_xxx_router()`

```python
@router.post("", status_code=201)
async def create_note(body: CreateNoteBody) -> JSONResponse:
    note = create_use_case.execute(CreateNoteInput(title=body.title, body=body.body))
    return JSONResponse({"id": note.id, "title": note.title, "body": note.body}, status_code=201)
```

### UseCase

- **Responsabilité unique** : implémenter une règle métier
- Une seule méthode : `execute(input_: XxxInput) -> XxxOutput`
- Pas d'`import fastapi`, pas d'`import sqlalchemy`
- N'appelle pas d'autres UseCases
- Testable avec `InMemoryRepository` seul

### RepositoryInterface

- Défini comme une ABC — le UseCase dépend uniquement de l'interface
- La même interface est implémentée par les versions InMemory et SQLAlchemy
- `find_all`, `find_by_id`, `save`, `update`, `delete`, `count`

### ConcreteRepository

- SQLAlchemy Core (sans ORM) avec des requêtes paramétrées
- Les requêtes sont exécutées via `SqlAlchemyQueryExecutor`
- Schéma de table : l'application exemple utilise un `src/example/schema.py` centralisé ; pour les nouveaux projets, définissez `ensure_schema()` dans le `sqlalchemy_repository.py` de chaque domaine et appelez-les toutes depuis `create_app()`

## Pile middleware

Les requêtes traversent chaque middleware de l'extérieur vers l'intérieur :

```
BearerTokenMiddleware        Authentification (Bearer Token)
ApiKeyAuthMiddleware         Authentification (API Key)
CORSMiddleware               CORS
ThrottleMiddleware           Limitation de débit (fenêtre fixe)
RequestSizeLimitMiddleware   Contrôle de la taille du payload
RequestLoggingMiddleware     Journalisation structurée (structlog)
RequestIdMiddleware          Génération / propagation de X-Request-ID
SecurityHeadersMiddleware    En-têtes de sécurité dans les réponses
ErrorHandlerMiddleware       Exceptions → RFC 9457 Problem Details
```

## Injection de dépendances

Le `Depends` de FastAPI est utilisé uniquement à la frontière HTTP. Les UseCases et les repositories sont câblés par injection de constructeur dans `app.py`.

```python
# app.py — câblage
note_repo = SqlAlchemyNoteRepository(executor)
app.include_router(make_note_router(
    list_use_case=ListNotesUseCase(note_repo),
    create_use_case=CreateNoteUseCase(note_repo),
    ...
))
```

## Structure d'un package de domaine

```
src/example/<domain>/
  __init__.py
  entity.py              — @dataclass(frozen=True, slots=True)
  repository.py          — ABC + implémentation InMemory
  exceptions.py          — XxxNotFoundException + ExceptionHandler
  use_case.py            — 5 UseCases + DTOs Input/Output
  handler.py             — factory de router FastAPI
  sqlalchemy_repository.py — backend SQL
```
