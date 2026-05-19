"""Tag use-cases — business logic, no HTTP or database knowledge."""

from dataclasses import dataclass

from .entity import Tag
from .exceptions import TagNotFoundException
from .repository import TagRepositoryInterface


@dataclass(frozen=True, slots=True)
class ListTagsInput:
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ListTagsOutput:
    items: list[Tag]
    limit: int
    offset: int
    total: int


class ListTagsUseCase:
    def __init__(self, repository: TagRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: ListTagsInput) -> ListTagsOutput:
        items = self._repository.find_all(input_.limit, input_.offset)
        total = self._repository.count()
        return ListTagsOutput(
            items=items,
            limit=input_.limit,
            offset=input_.offset,
            total=total,
        )


@dataclass(frozen=True, slots=True)
class GetTagInput:
    tag_id: int


class GetTagUseCase:
    def __init__(self, repository: TagRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: GetTagInput) -> Tag:
        tag = self._repository.find_by_id(input_.tag_id)
        if tag is None:
            raise TagNotFoundException(input_.tag_id)
        return tag


@dataclass(frozen=True, slots=True)
class CreateTagInput:
    name: str


class CreateTagUseCase:
    def __init__(self, repository: TagRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: CreateTagInput) -> Tag:
        return self._repository.save(input_.name)


@dataclass(frozen=True, slots=True)
class UpdateTagInput:
    tag_id: int
    name: str


class UpdateTagUseCase:
    def __init__(self, repository: TagRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: UpdateTagInput) -> Tag:
        tag = self._repository.update(input_.tag_id, input_.name)
        if tag is None:
            raise TagNotFoundException(input_.tag_id)
        return tag


@dataclass(frozen=True, slots=True)
class DeleteTagInput:
    tag_id: int


class DeleteTagUseCase:
    def __init__(self, repository: TagRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: DeleteTagInput) -> None:
        deleted = self._repository.delete(input_.tag_id)
        if not deleted:
            raise TagNotFoundException(input_.tag_id)
