# Implementar um novo domínio

Este tutorial mostra como adicionar o domínio `Tag` do zero.
Ao construir cada camada em ordem, você vai entender como a arquitetura limpa do nene2-python se encaixa.

> **Pré-requisito**: Complete o tutorial [Primeiros passos](getting-started.md) antes.

## O que vamos construir

```
GET    /tags           — listar tags
POST   /tags           — criar uma tag
GET    /tags/{tag_id}  — buscar uma tag
PUT    /tags/{tag_id}  — atualizar uma tag
DELETE /tags/{tag_id}  — deletar uma tag
```

## Passo 1: Entidade

Crie `src/example/tag/entity.py`.

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Tag:
    id: int
    name: str
```

`frozen=True` torna o objeto imutável; `slots=True` reduz o consumo de memória.

## Passo 2: Interface do Repository

Defina o contrato em `src/example/tag/repository.py`.

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

## Passo 3: Implementação InMemory

Forneça um repository em memória para testes — sem banco de dados necessário.

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
    # ... outros métodos
```

## Passo 4: UseCase

`src/example/tag/use_case.py` contém a lógica de negócio — sem imports de HTTP ou banco de dados.

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

## Passo 5: HTTP Handler

`src/example/tag/handler.py` — apenas três passos: **parse → use-case → response**.

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

## Passo 6: Conectar ao app.py

Adicione o router em `src/example/app.py`.

```python
app.include_router(make_tag_router(
    list_use_case=ListTagsUseCase(tag_repo),
    ...
))
```

## Passo 7: Escrever os testes

```python
# tests/example/tag/test_tag_use_case.py
def test_create_tag() -> None:
    repo = InMemoryTagRepository()
    tag = CreateTagUseCase(repo).execute(CreateTagInput(name="python"))
    assert tag.name == "python"
```

## Pronto

O domínio Tag que você acabou de construir segue o mesmo padrão do domínio Comment em `src/example/comment/`.
Veja `src/example/tag/` para a implementação de referência completa.

## Próximos passos

- [Adicionar um novo domínio](../how-to/add-new-domain.md) — um checklist para adições de domínio com qualidade de produção
- [Visão geral da arquitetura](../explanation/architecture.md) — entenda o papel de cada camada
