"""Repository contract tests for CommentRepository."""

import pytest
from sqlalchemy import create_engine

from example.comment.repository import CommentRepositoryInterface, InMemoryCommentRepository
from example.comment.sqlalchemy_repository import SqlAlchemyCommentRepository
from nene2.database import SqlAlchemyQueryExecutor


def _create_schema(executor: SqlAlchemyQueryExecutor) -> None:
    executor.write(
        "CREATE TABLE IF NOT EXISTS comments ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "note_id INTEGER NOT NULL,"
        "body TEXT NOT NULL,"
        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
        ")"
    )


def _sqlalchemy_repo() -> SqlAlchemyCommentRepository:
    engine = create_engine("sqlite:///:memory:")
    executor = SqlAlchemyQueryExecutor(engine)
    _create_schema(executor)
    return SqlAlchemyCommentRepository(executor)


@pytest.fixture(params=["inmemory", "sqlalchemy"])
def repo(request: pytest.FixtureRequest) -> CommentRepositoryInterface:
    if request.param == "inmemory":
        return InMemoryCommentRepository()
    return _sqlalchemy_repo()


def test_save_and_find_by_id(repo: CommentRepositoryInterface) -> None:
    comment = repo.save(note_id=1, body="test")
    found = repo.find_by_id(comment.id)
    assert found == comment


def test_find_by_id_returns_none_when_missing(repo: CommentRepositoryInterface) -> None:
    assert repo.find_by_id(9999) is None


def test_find_all_by_note_filters_correctly(repo: CommentRepositoryInterface) -> None:
    repo.save(note_id=1, body="note1")
    repo.save(note_id=2, body="note2")
    items = repo.find_all_by_note(note_id=1, limit=10, offset=0)
    assert len(items) == 1
    assert items[0].body == "note1"


def test_count_by_note(repo: CommentRepositoryInterface) -> None:
    repo.save(note_id=1, body="a")
    repo.save(note_id=1, body="b")
    repo.save(note_id=2, body="c")
    assert repo.count_by_note(1) == 2
    assert repo.count_by_note(2) == 1


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


def test_delete_returns_false_for_missing(repo: CommentRepositoryInterface) -> None:
    assert repo.delete(9999) is False
