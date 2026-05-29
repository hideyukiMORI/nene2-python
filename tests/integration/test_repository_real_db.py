"""Note repository contract verified against real PostgreSQL / MySQL servers.

Mirrors the SQLite contract in tests/example/note/test_note_repository.py, plus a
regression for the multi-DB INSERT-PK bug: psycopg2 exposes no ``lastrowid``, so
``save()`` must derive the new PK another way (lastval) rather than returning
``rowcount`` (#747).
"""

import pytest

from nene2.database import SqlAlchemyQueryExecutor
from src.example.note.entity import Note
from src.example.note.sqlalchemy_repository import SqlAlchemyNoteRepository


@pytest.fixture
def repo(real_db_executor: SqlAlchemyQueryExecutor) -> SqlAlchemyNoteRepository:
    return SqlAlchemyNoteRepository(real_db_executor)


def test_save_returns_sequential_pks(repo: SqlAlchemyNoteRepository) -> None:
    first = repo.save("A", "a")
    second = repo.save("B", "b")
    assert (first.id, second.id) == (1, 2)


def test_save_and_find_round_trip(repo: SqlAlchemyNoteRepository) -> None:
    note = repo.save("Hello", "World")
    assert repo.find_by_id(note.id) == note


def test_find_by_id_returns_none_when_missing(repo: SqlAlchemyNoteRepository) -> None:
    assert repo.find_by_id(9999) is None


def test_find_all_respects_limit_and_offset(repo: SqlAlchemyNoteRepository) -> None:
    for i in range(5):
        repo.save(f"Note {i}", "body")
    page = repo.find_all(limit=2, offset=2)
    assert [n.title for n in page] == ["Note 2", "Note 3"]


def test_count_reflects_saved_notes(repo: SqlAlchemyNoteRepository) -> None:
    repo.save("T", "B")
    repo.save("T2", "B2")
    assert repo.count() == 2


def test_update_changes_title_and_body(repo: SqlAlchemyNoteRepository) -> None:
    note = repo.save("Old", "old body")
    assert repo.update(note.id, "New", "new body") == Note(id=note.id, title="New", body="new body")


def test_update_returns_none_for_missing_id(repo: SqlAlchemyNoteRepository) -> None:
    assert repo.update(9999, "T", "B") is None


def test_delete_removes_note(repo: SqlAlchemyNoteRepository) -> None:
    note = repo.save("T", "B")
    repo.delete(note.id)
    assert repo.find_by_id(note.id) is None


def test_delete_returns_false_for_missing_id(repo: SqlAlchemyNoteRepository) -> None:
    assert repo.delete(9999) is False
