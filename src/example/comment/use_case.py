"""Comment use-cases — business logic, no HTTP or database knowledge."""

from dataclasses import dataclass

from example.note.exceptions import NoteNotFoundException
from example.note.repository import NoteRepositoryInterface

from .entity import Comment
from .exceptions import CommentNotFoundException
from .repository import CommentRepositoryInterface


@dataclass(frozen=True, slots=True)
class ListCommentsInput:
    note_id: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ListCommentsOutput:
    items: list[Comment]
    note_id: int
    limit: int
    offset: int
    total: int


class ListCommentsUseCase:
    def __init__(self, repository: CommentRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: ListCommentsInput) -> ListCommentsOutput:
        items = self._repository.find_all_by_note(input_.note_id, input_.limit, input_.offset)
        total = self._repository.count_by_note(input_.note_id)
        return ListCommentsOutput(
            items=items,
            note_id=input_.note_id,
            limit=input_.limit,
            offset=input_.offset,
            total=total,
        )


@dataclass(frozen=True, slots=True)
class GetCommentInput:
    comment_id: int


class GetCommentUseCase:
    def __init__(self, repository: CommentRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: GetCommentInput) -> Comment:
        comment = self._repository.find_by_id(input_.comment_id)
        if comment is None:
            raise CommentNotFoundException(input_.comment_id)
        return comment


@dataclass(frozen=True, slots=True)
class CreateCommentInput:
    note_id: int
    body: str


class CreateCommentUseCase:
    def __init__(
        self,
        comment_repository: CommentRepositoryInterface,
        note_repository: NoteRepositoryInterface,
    ) -> None:
        self._comment_repository = comment_repository
        self._note_repository = note_repository

    def execute(self, input_: CreateCommentInput) -> Comment:
        if self._note_repository.find_by_id(input_.note_id) is None:
            raise NoteNotFoundException(input_.note_id)
        return self._comment_repository.save(input_.note_id, input_.body)


@dataclass(frozen=True, slots=True)
class UpdateCommentInput:
    comment_id: int
    body: str


class UpdateCommentUseCase:
    def __init__(self, repository: CommentRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: UpdateCommentInput) -> Comment:
        comment = self._repository.update(input_.comment_id, input_.body)
        if comment is None:
            raise CommentNotFoundException(input_.comment_id)
        return comment


@dataclass(frozen=True, slots=True)
class DeleteCommentInput:
    comment_id: int


class DeleteCommentUseCase:
    def __init__(self, repository: CommentRepositoryInterface) -> None:
        self._repository = repository

    def execute(self, input_: DeleteCommentInput) -> None:
        deleted = self._repository.delete(input_.comment_id)
        if not deleted:
            raise CommentNotFoundException(input_.comment_id)
