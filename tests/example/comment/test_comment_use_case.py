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


def _repo() -> InMemoryCommentRepository:
    return InMemoryCommentRepository()


def test_create_and_list() -> None:
    repo = _repo()
    CreateCommentUseCase(repo).execute(CreateCommentInput(note_id=1, body="hello"))
    result = ListCommentsUseCase(repo).execute(ListCommentsInput(note_id=1, limit=10, offset=0))
    assert result.total == 1
    assert result.items[0].body == "hello"


def test_list_filters_by_note_id() -> None:
    repo = _repo()
    CreateCommentUseCase(repo).execute(CreateCommentInput(note_id=1, body="note1 comment"))
    CreateCommentUseCase(repo).execute(CreateCommentInput(note_id=2, body="note2 comment"))
    result = ListCommentsUseCase(repo).execute(ListCommentsInput(note_id=1, limit=10, offset=0))
    assert result.total == 1
    assert result.items[0].body == "note1 comment"


def test_get_returns_comment() -> None:
    repo = _repo()
    comment = CreateCommentUseCase(repo).execute(CreateCommentInput(note_id=1, body="body"))
    fetched = GetCommentUseCase(repo).execute(GetCommentInput(comment_id=comment.id))
    assert fetched == comment


def test_get_raises_when_not_found() -> None:
    repo = _repo()
    with pytest.raises(CommentNotFoundException):
        GetCommentUseCase(repo).execute(GetCommentInput(comment_id=9999))


def test_update_changes_body() -> None:
    repo = _repo()
    comment = CreateCommentUseCase(repo).execute(CreateCommentInput(note_id=1, body="old"))
    updated = UpdateCommentUseCase(repo).execute(
        UpdateCommentInput(comment_id=comment.id, body="new")
    )
    assert updated.body == "new"


def test_update_raises_when_not_found() -> None:
    repo = _repo()
    with pytest.raises(CommentNotFoundException):
        UpdateCommentUseCase(repo).execute(UpdateCommentInput(comment_id=9999, body="x"))


def test_delete_removes_comment() -> None:
    repo = _repo()
    comment = CreateCommentUseCase(repo).execute(CreateCommentInput(note_id=1, body="bye"))
    DeleteCommentUseCase(repo).execute(DeleteCommentInput(comment_id=comment.id))
    with pytest.raises(CommentNotFoundException):
        GetCommentUseCase(repo).execute(GetCommentInput(comment_id=comment.id))


def test_delete_raises_when_not_found() -> None:
    repo = _repo()
    with pytest.raises(CommentNotFoundException):
        DeleteCommentUseCase(repo).execute(DeleteCommentInput(comment_id=9999))
