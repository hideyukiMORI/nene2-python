"""Note use-cases — business logic, no HTTP or database knowledge."""

from dataclasses import dataclass

from .entity import Note
from .exceptions import NoteNotFoundException
from .repository import NoteRepositoryInterface


@dataclass(frozen=True, slots=True)
class ListNotesInput:
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
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

    def execute(self, note_id: int) -> Note:
        note = self._repository.find_by_id(note_id)
        if note is None:
            raise NoteNotFoundException(note_id)
        return note


@dataclass(frozen=True, slots=True)
class UpdateNoteInput:
    note_id: int
    title: str
    body: str


class UpdateNoteUseCase:
    def __init__(self, repository: NoteRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: UpdateNoteInput) -> Note:
        note = self._repository.update(input_.note_id, input_.title, input_.body)
        if note is None:
            raise NoteNotFoundException(input_.note_id)
        return note


@dataclass(frozen=True, slots=True)
class DeleteNoteInput:
    note_id: int


class DeleteNoteUseCase:
    def __init__(self, repository: NoteRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: DeleteNoteInput) -> None:
        deleted = self._repository.delete(input_.note_id)
        if not deleted:
            raise NoteNotFoundException(input_.note_id)
