# 新しいドメインを実装する

このチュートリアルでは、`Tag` ドメインを例に nene2-python のクリーンアーキテクチャを体験します。
各レイヤーを順番に実装することで、フレームワークの構造全体を理解できます。

> **前提**: [はじめての nene2-python](getting-started.md) を完了していること

## 実装するもの

```
GET    /tags           — タグ一覧
POST   /tags           — タグ作成
GET    /tags/{tag_id}  — タグ取得
PUT    /tags/{tag_id}  — タグ更新
DELETE /tags/{tag_id}  — タグ削除
```

## ステップ 1: Entity を作る

`src/example/tag/entity.py` を作成します。

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Tag:
    id: int
    name: str
```

`frozen=True` で不変オブジェクト、`slots=True` でメモリ効率を高めています。

## ステップ 2: Repository Interface を作る

`src/example/tag/repository.py` に ABC を定義します。

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

## ステップ 3: InMemory 実装を作る

テスト用の InMemory リポジトリを実装します。

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
    # ... 省略
```

## ステップ 4: UseCase を作る

`src/example/tag/use_case.py` に UseCase を定義します。UseCase は HTTP・DB を知りません。

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

## ステップ 5: Handler を作る

`src/example/tag/handler.py` に HTTP ルーターを定義します。**parse → use-case → response** の 3 ステップだけ。

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

## ステップ 6: app.py に組み込む

`src/example/app.py` の `create_app()` にルーターを追加します。

```python
app.include_router(make_tag_router(
    list_use_case=ListTagsUseCase(tag_repo),
    ...
))
```

## ステップ 7: テストを書く

```python
# tests/example/tag/test_tag_use_case.py
def test_create_tag() -> None:
    repo = InMemoryTagRepository()
    tag = CreateTagUseCase(repo).execute(CreateTagInput(name="python"))
    assert tag.name == "python"
```

## 完了

実装した Tag ドメインは Comment ドメイン (`src/example/comment/`) と同じ構造です。
実際の実装は `src/example/tag/` を参照してください。

## 次のステップ

- [新しいドメインを追加する](../how-to/add-new-domain.md) — チェックリスト形式の実践ガイド
- [アーキテクチャ概要](../explanation/architecture.md) — 各レイヤーの役割を深く理解する
