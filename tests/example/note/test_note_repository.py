"""Repository contract tests — run against both InMemory and SqlAlchemy implementations."""

import pytest
from sqlalchemy import create_engine

from nene2.database import SqlAlchemyQueryExecutor
from src.example.note.entity import Note
from src.example.note.repository import InMemoryNoteRepository, NoteRepositoryInterface
from src.example.note.sqlalchemy_repository import SqlAlchemyNoteRepository


def _create_schema(executor: SqlAlchemyQueryExecutor) -> None:
    executor.write(
        "CREATE TABLE IF NOT EXISTS notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "title TEXT NOT NULL,"
        "body TEXT NOT NULL,"
        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
        "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"
        ")"
    )


def _sqlalchemy_repo() -> SqlAlchemyNoteRepository:
    engine = create_engine("sqlite:///:memory:")
    executor = SqlAlchemyQueryExecutor(engine)
    _create_schema(executor)
    return SqlAlchemyNoteRepository(executor)


@pytest.fixture(params=["inmemory", "sqlalchemy"])
def repo(request: pytest.FixtureRequest) -> NoteRepositoryInterface:
    if request.param == "inmemory":
        return InMemoryNoteRepository()
    return _sqlalchemy_repo()


def test_save_and_find_by_id(repo: NoteRepositoryInterface) -> None:
    note = repo.save("Hello", "World")
    found = repo.find_by_id(note.id)
    assert found == note


def test_find_by_id_returns_none_when_missing(repo: NoteRepositoryInterface) -> None:
    assert repo.find_by_id(9999) is None


def test_find_all_returns_saved_notes(repo: NoteRepositoryInterface) -> None:
    repo.save("A", "a")
    repo.save("B", "b")
    items = repo.find_all(limit=10, offset=0)
    assert len(items) == 2
    assert items[0].title == "A"
    assert items[1].title == "B"


def test_find_all_respects_limit_and_offset(repo: NoteRepositoryInterface) -> None:
    for i in range(5):
        repo.save(f"Note {i}", "body")
    page = repo.find_all(limit=2, offset=2)
    assert len(page) == 2
    assert page[0].title == "Note 2"


def test_count_reflects_saved_notes(repo: NoteRepositoryInterface) -> None:
    assert repo.count() == 0
    repo.save("T", "B")
    repo.save("T2", "B2")
    assert repo.count() == 2


def test_update_changes_title_and_body(repo: NoteRepositoryInterface) -> None:
    note = repo.save("Old", "old body")
    updated = repo.update(note.id, "New", "new body")
    assert updated == Note(id=note.id, title="New", body="new body")


def test_update_returns_none_for_missing_id(repo: NoteRepositoryInterface) -> None:
    assert repo.update(9999, "T", "B") is None


def test_delete_removes_note(repo: NoteRepositoryInterface) -> None:
    note = repo.save("T", "B")
    assert repo.delete(note.id) is True
    assert repo.find_by_id(note.id) is None


def test_delete_returns_false_for_missing_id(repo: NoteRepositoryInterface) -> None:
    assert repo.delete(9999) is False
