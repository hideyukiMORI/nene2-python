# Implémenter un nouveau domaine

Ce tutoriel vous guide dans l'ajout du domaine `Tag` de zéro.
En construisant chaque couche dans l'ordre, vous découvrirez comment l'architecture propre de nene2-python s'articule.

> **Prérequis** : Complétez d'abord [Premiers pas](getting-started.md).

## Ce que nous allons construire

```
GET    /tags           — lister les tags
POST   /tags           — créer un tag
GET    /tags/{tag_id}  — obtenir un tag
PUT    /tags/{tag_id}  — modifier un tag
DELETE /tags/{tag_id}  — supprimer un tag
```

## Étape 1 : Entité

Créez `src/example/tag/entity.py`.

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Tag:
    id: int
    name: str
```

`frozen=True` rend l'objet immuable ; `slots=True` réduit la consommation mémoire.

## Étape 2 : Interface de repository

Définissez le contrat dans `src/example/tag/repository.py`.

```python
from abc import ABC, abstractmethod
from .entity import Tag

class TagRepositoryInterface(ABC):
    @abstractmethod
    def find_all(self, limit: int, offset: int) -> list[Tag]: ...

    @abstractmethod
    def find_by_id(self, tag_id: int) -> Tag | None: ...

    @abstractmethod
    def save(self, name: str) -> Tag: ...

    @abstractmethod
    def update(self, tag_id: int, name: str) -> Tag | None: ...

    @abstractmethod
    def delete(self, tag_id: int) -> bool: ...

    @abstractmethod
    def count(self) -> int: ...
```

## Étape 3 : Implémentation en mémoire

Fournissez un repository en mémoire pour les tests — aucune base de données requise.

```python
class InMemoryTagRepository(TagRepositoryInterface):
    def __init__(self) -> None:
        self._store: dict[int, Tag] = {}
        self._next_id = 1

    def save(self, name: str) -> Tag:
        tag = Tag(id=self._next_id, name=name)
        self._store[self._next_id] = tag
        self._next_id += 1
        return tag
    # ... autres méthodes
```

## Étape 4 : UseCase

`src/example/tag/use_case.py` contient la logique métier — sans imports HTTP ni base de données.

```python
from dataclasses import dataclass
from .entity import Tag
from .exceptions import TagNotFoundException
from .repository import TagRepositoryInterface

@dataclass(frozen=True)
class CreateTagInput:
    name: str

class CreateTagUseCase:
    def __init__(self, repository: TagRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: CreateTagInput) -> Tag:
        return self._repository.save(input_.name)
```

## Étape 5 : Handler HTTP

`src/example/tag/handler.py` — uniquement trois étapes : **parse → use-case → response**.

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .use_case import CreateTagInput, CreateTagUseCase

class CreateTagBody(BaseModel):
    name: str

def make_tag_router(create_use_case: CreateTagUseCase, ...) -> APIRouter:
    router = APIRouter(prefix="/tags", tags=["tags"])

    @router.post("", status_code=201)
    async def create_tag(body: CreateTagBody) -> JSONResponse:
        tag = create_use_case.execute(CreateTagInput(name=body.name))
        return JSONResponse({"id": tag.id, "name": tag.name}, status_code=201)

    return router
```

## Étape 6 : Intégration dans app.py

Ajoutez le router dans `src/example/app.py`.

```python
app.include_router(make_tag_router(
    list_use_case=ListTagsUseCase(tag_repo),
    ...
))
```

## Étape 7 : Écrire les tests

```python
# tests/example/tag/test_tag_use_case.py
def test_create_tag() -> None:
    repo = InMemoryTagRepository()
    tag = CreateTagUseCase(repo).execute(CreateTagInput(name="python"))
    assert tag.name == "python"
```

## Terminé

Le domaine Tag que vous venez de créer correspond au domaine Comment dans `src/example/comment/`.
Consultez `src/example/tag/` pour l'implémentation de référence complète.

## Étapes suivantes

- [Ajouter un nouveau domaine](../how-to/add-new-domain.md) — une checklist pour des ajouts de domaine de qualité production
- [Vue d'ensemble de l'architecture](../explanation/architecture.md) — comprendre le rôle de chaque couche
