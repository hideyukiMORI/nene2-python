"""Unit tests for Comment UseCases (no HTTP, no DB)."""

import pytest

from example.comment.exceptions import CommentNotFoundException
from example.comment.repository import InMemoryCommentRepository
from example.comment.use_case import (
    CreateCommentInput,
    CreateCommentUseCase,
    DeleteCommentInput,
    DeleteCommentUseCase,
    GetCommentInput,
    GetCommentUseCase,
    ListCommentsInput,
    ListCommentsUseCase,
    UpdateCommentInput,
    UpdateCommentUseCase,
)
from example.note.exceptions import NoteNotFoundException
from example.note.repository import InMemoryNoteRepository


def _repos() -> tuple[InMemoryCommentRepository, InMemoryNoteRepository]:
    return InMemoryCommentRepository(), InMemoryNoteRepository()


def _create_use_case(
    comment_repo: InMemoryCommentRepository, note_repo: InMemoryNoteRepository
) -> CreateCommentUseCase:
    return CreateCommentUseCase(comment_repo, note_repo)


def test_create_and_list() -> None:
    comment_repo, note_repo = _repos()
    note_repo.save("title", "body")
    _create_use_case(comment_repo, note_repo).execute(CreateCommentInput(note_id=1, body="hello"))
    result = ListCommentsUseCase(comment_repo).execute(
        ListCommentsInput(note_id=1, limit=10, offset=0)
    )
    assert result.total == 1
    assert result.items[0].body == "hello"


def test_list_filters_by_note_id() -> None:
    comment_repo, note_repo = _repos()
    note_repo.save("n1", "b1")
    note_repo.save("n2", "b2")
    uc = _create_use_case(comment_repo, note_repo)
    uc.execute(CreateCommentInput(note_id=1, body="note1 comment"))
    uc.execute(CreateCommentInput(note_id=2, body="note2 comment"))
    result = ListCommentsUseCase(comment_repo).execute(
        ListCommentsInput(note_id=1, limit=10, offset=0)
    )
    assert result.total == 1
    assert result.items[0].body == "note1 comment"


def test_create_raises_when_note_not_found() -> None:
    comment_repo, note_repo = _repos()
    with pytest.raises(NoteNotFoundException):
        _create_use_case(comment_repo, note_repo).execute(
            CreateCommentInput(note_id=9999, body="orphan")
        )


def test_get_returns_comment() -> None:
    comment_repo, note_repo = _repos()
    note_repo.save("title", "body")
    comment = _create_use_case(comment_repo, note_repo).execute(
        CreateCommentInput(note_id=1, body="body")
    )
    fetched = GetCommentUseCase(comment_repo).execute(GetCommentInput(comment_id=comment.id))
    assert fetched == comment


def test_get_raises_when_not_found() -> None:
    comment_repo, _ = _repos()
    with pytest.raises(CommentNotFoundException):
        GetCommentUseCase(comment_repo).execute(GetCommentInput(comment_id=9999))


def test_update_changes_body() -> None:
    comment_repo, note_repo = _repos()
    note_repo.save("title", "body")
    comment = _create_use_case(comment_repo, note_repo).execute(
        CreateCommentInput(note_id=1, body="old")
    )
    updated = UpdateCommentUseCase(comment_repo).execute(
        UpdateCommentInput(comment_id=comment.id, body="new")
    )
    assert updated.body == "new"


def test_update_raises_when_not_found() -> None:
    comment_repo, _ = _repos()
    with pytest.raises(CommentNotFoundException):
        UpdateCommentUseCase(comment_repo).execute(UpdateCommentInput(comment_id=9999, body="x"))


def test_delete_removes_comment() -> None:
    comment_repo, note_repo = _repos()
    note_repo.save("title", "body")
    comment = _create_use_case(comment_repo, note_repo).execute(
        CreateCommentInput(note_id=1, body="bye")
    )
    DeleteCommentUseCase(comment_repo).execute(DeleteCommentInput(comment_id=comment.id))
    with pytest.raises(CommentNotFoundException):
        GetCommentUseCase(comment_repo).execute(GetCommentInput(comment_id=comment.id))


def test_delete_raises_when_not_found() -> None:
    comment_repo, _ = _repos()
    with pytest.raises(CommentNotFoundException):
        DeleteCommentUseCase(comment_repo).execute(DeleteCommentInput(comment_id=9999))
