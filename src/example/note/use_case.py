"""Note use-cases — business logic, no HTTP or database knowledge."""

from dataclasses import dataclass

from nene2.validation.exceptions import ValidationError, ValidationException

from .entity import Note
from .exceptions import NoteNotFoundException
from .repository import NoteRepositoryInterface

MAX_NOTE_TITLE_LENGTH = 500
MAX_NOTE_BODY_LENGTH = 10_000


def _validate_note_content(title: str, body: str) -> None:
    """Domain invariant for a note's content — enforced on every surface (HTTP and MCP)."""
    errors: list[ValidationError] = []
    if not title.strip():
        errors.append(ValidationError("title", "Title must not be empty.", "required"))
    elif len(title) > MAX_NOTE_TITLE_LENGTH:
        errors.append(
            ValidationError(
                "title", f"Title must be at most {MAX_NOTE_TITLE_LENGTH} characters.", "too_long"
            )
        )
    if not body.strip():
        errors.append(ValidationError("body", "Body must not be empty.", "required"))
    elif len(body) > MAX_NOTE_BODY_LENGTH:
        errors.append(
            ValidationError(
                "body", f"Body must be at most {MAX_NOTE_BODY_LENGTH} characters.", "too_long"
            )
        )
    if errors:
        raise ValidationException(errors)


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

    def __post_init__(self) -> None:
        _validate_note_content(self.title, self.body)


class CreateNoteUseCase:
    def __init__(self, repository: NoteRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: CreateNoteInput) -> Note:
        return self._repository.save(input_.title, input_.body)


@dataclass(frozen=True, slots=True)
class GetNoteInput:
    note_id: int


class GetNoteUseCase:
    def __init__(self, repository: NoteRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: GetNoteInput) -> Note:
        note = self._repository.find_by_id(input_.note_id)
        if note is None:
            raise NoteNotFoundException(input_.note_id)
        return note


@dataclass(frozen=True, slots=True)
class UpdateNoteInput:
    note_id: int
    title: str
    body: str

    def __post_init__(self) -> None:
        _validate_note_content(self.title, self.body)


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
