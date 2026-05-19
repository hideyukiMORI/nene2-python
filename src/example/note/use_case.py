"""Note use-cases — business logic, no HTTP or database knowledge."""

from dataclasses import dataclass

from .entity import Note
from .repository import NoteRepositoryInterface


@dataclass(frozen=True)
class ListNotesInput:
    limit: int
    offset: int


@dataclass(frozen=True)
class ListNotesOutput:
    items: list[Note]
    limit: int
    offset: int
    total: int


class ListNotesUseCase:
    def __init__(self, repository: NoteRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: ListNotesInput) -> ListNotesOutput:
        items = self._repository.find_all(input_.limit, input_.offset)
        total = self._repository.count()
        return ListNotesOutput(
            items=items,
            limit=input_.limit,
            offset=input_.offset,
            total=total,
        )


@dataclass(frozen=True)
class CreateNoteInput:
    title: str
    body: str


class CreateNoteUseCase:
    def __init__(self, repository: NoteRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: CreateNoteInput) -> Note:
        return self._repository.save(input_.title, input_.body)


class GetNoteUseCase:
    def __init__(self, repository: NoteRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, note_id: int) -> Note | None:
        return self._repository.find_by_id(note_id)
