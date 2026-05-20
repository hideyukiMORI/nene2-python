"""Repository contract tests for CommentRepository."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine

from example.comment.repository import CommentRepositoryInterface, InMemoryCommentRepository
from example.comment.sqlalchemy_repository import SqlAlchemyCommentRepository
from example.note.sqlalchemy_repository import SqlAlchemyNoteRepository
from example.schema import ensure_schema
from nene2.database import SqlAlchemyQueryExecutor


@pytest.fixture(params=["inmemory", "sqlalchemy"])
def repo(request: pytest.FixtureRequest) -> Generator[CommentRepositoryInterface, None, None]:
    if request.param == "inmemory":
        yield InMemoryCommentRepository()
        return
    engine = create_engine("sqlite:///:memory:")
    ensure_schema(engine)
    executor = SqlAlchemyQueryExecutor(engine)
    comment_repo = SqlAlchemyCommentRepository(executor)
    note_repo = SqlAlchemyNoteRepository(executor)
    note_repo.save("Note", "body")
    yield comment_repo
    engine.dispose()


def test_save_and_find_by_id(repo: CommentRepositoryInterface) -> None:
    comment = repo.save(note_id=1, body="test")
    found = repo.find_by_id(comment.id)
    assert found == comment


def test_find_by_id_returns_none_when_missing(repo: CommentRepositoryInterface) -> None:
    assert repo.find_by_id(9999) is None


def test_find_all_by_note_filters_correctly(repo: CommentRepositoryInterface) -> None:
    repo.save(note_id=1, body="note1")
    repo.save(note_id=1, body="note1b")
    items = repo.find_all_by_note(note_id=1, limit=10, offset=0)
    assert len(items) == 2
    assert items[0].body == "note1"


def test_count_by_note(repo: CommentRepositoryInterface) -> None:
    repo.save(note_id=1, body="a")
    repo.save(note_id=1, body="b")
    assert repo.count_by_note(1) == 2
    assert repo.count_by_note(9999) == 0


def test_update_changes_body(repo: CommentRepositoryInterface) -> None:
    comment = repo.save(note_id=1, body="old")
    updated = repo.update(comment.id, "new")
    assert updated is not None
    assert updated.body == "new"
    assert updated.note_id == 1


def test_update_returns_none_for_missing(repo: CommentRepositoryInterface) -> None:
    assert repo.update(9999, "x") is None


def test_delete_removes_comment(repo: CommentRepositoryInterface) -> None:
    comment = repo.save(note_id=1, body="bye")
    assert repo.delete(comment.id) is True
    assert repo.find_by_id(comment.id) is None


def test_delete_returns_false_for_missing() -> None:
    assert InMemoryCommentRepository().delete(9999) is False
