# 实现新领域

本教程带您从零开始添加 `Tag` 领域，按层逐步构建，直观展示 nene2-python 整洁架构的组织方式。

> **前提条件**：请先完成 [入门指南](getting-started.md)。

## 目标

```
GET    /tags           — 获取标签列表
POST   /tags           — 创建标签
GET    /tags/{tag_id}  — 获取单个标签
PUT    /tags/{tag_id}  — 更新标签
DELETE /tags/{tag_id}  — 删除标签
```

## 第 1 步：实体

创建 `src/example/tag/entity.py`。

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Tag:
    id: int
    name: str
```

`frozen=True` 使对象不可变；`slots=True` 减少内存开销。

## 第 2 步：Repository 接口

在 `src/example/tag/repository.py` 中定义契约。

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

## 第 3 步：InMemory 实现

为测试提供内存中的 repository，无需数据库。

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
    # ... 其他方法
```

## 第 4 步：UseCase

`src/example/tag/use_case.py` 包含业务逻辑，不引入任何 HTTP 或数据库依赖。

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

## 第 5 步：HTTP Handler

`src/example/tag/handler.py` — 仅三步：**解析 → UseCase → 响应**。

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

## 第 6 步：接入 app.py

在 `src/example/app.py` 中注册 router。

```python
app.include_router(make_tag_router(
    list_use_case=ListTagsUseCase(tag_repo),
    ...
))
```

## 第 7 步：编写测试

```python
# tests/example/tag/test_tag_use_case.py
def test_create_tag() -> None:
    repo = InMemoryTagRepository()
    tag = CreateTagUseCase(repo).execute(CreateTagInput(name="python"))
    assert tag.name == "python"
```

## 完成

您刚才构建的 Tag 领域与 `src/example/comment/` 中的 Comment 领域结构完全一致。
完整的参考实现请参阅 `src/example/tag/`。

## 下一步

- [添加新领域](../how-to/add-new-domain.md) — 面向生产质量的领域添加检查清单
- [架构概览](../explanation/architecture.md) — 深入理解各层的职责
