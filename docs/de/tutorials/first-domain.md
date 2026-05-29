# Eine neue Domain implementieren

Dieses Tutorial führt Sie Schritt für Schritt durch das Hinzufügen der `Tag`-Domain.
Indem Sie jede Schicht der Reihe nach aufbauen, sehen Sie, wie die Clean Architecture von nene2-python zusammenpasst.

> **Voraussetzung**: Schließen Sie zuerst [Erste Schritte](getting-started.md) ab.

## Was wir erstellen

```
GET    /tags           — Tags auflisten
POST   /tags           — Tag erstellen
GET    /tags/{tag_id}  — Tag abrufen
PUT    /tags/{tag_id}  — Tag aktualisieren
DELETE /tags/{tag_id}  — Tag löschen
```

## Schritt 1: Entity

Erstellen Sie `src/example/tag/entity.py`.

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Tag:
    id: int
    name: str
```

`frozen=True` macht das Objekt unveränderlich; `slots=True` reduziert den Speicherbedarf.

## Schritt 2: Repository-Interface

Definieren Sie den Vertrag in `src/example/tag/repository.py`.

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

## Schritt 3: InMemory-Implementierung

Stellen Sie ein In-Memory-Repository für Tests bereit — keine Datenbank erforderlich.

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
    # ... weitere Methoden
```

## Schritt 4: UseCase

`src/example/tag/use_case.py` enthält die Geschäftslogik — keine HTTP- oder Datenbankimporte.

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

## Schritt 5: HTTP-Handler

`src/example/tag/handler.py` — nur drei Schritte: **parse → use-case → response**.

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

## Schritt 6: In app.py einbinden

Fügen Sie den router in `src/example/app.py` hinzu.

```python
app.include_router(make_tag_router(
    list_use_case=ListTagsUseCase(tag_repo),
    ...
))
```

## Schritt 7: Tests schreiben

```python
# tests/example/tag/test_tag_use_case.py
def test_create_tag() -> None:
    repo = InMemoryTagRepository()
    tag = CreateTagUseCase(repo).execute(CreateTagInput(name="python"))
    assert tag.name == "python"
```

## Fertig

Die Tag-Domain, die Sie soeben erstellt haben, entspricht der Comment-Domain unter `src/example/comment/`.
Die vollständige Referenzimplementierung finden Sie unter `src/example/tag/`.

## Nächste Schritte

- [Neue Domain hinzufügen](../how-to/add-new-domain.md) — eine Checkliste für produktionsreife Domain-Ergänzungen
- [Architekturübersicht](../explanation/architecture.md) — die Rolle jeder Schicht verstehen
