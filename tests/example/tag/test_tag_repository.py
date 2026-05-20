"""Repository contract tests — run against both InMemory and SqlAlchemy implementations."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine

from nene2.database import SqlAlchemyQueryExecutor
from src.example.tag.entity import Tag
from src.example.tag.repository import InMemoryTagRepository, TagRepositoryInterface
from src.example.tag.sqlalchemy_repository import SqlAlchemyTagRepository


def _create_schema(executor: SqlAlchemyQueryExecutor) -> None:
    executor.write(
        "CREATE TABLE IF NOT EXISTS tags ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "name TEXT NOT NULL UNIQUE,"
        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
        ")"
    )


@pytest.fixture(params=["inmemory", "sqlalchemy"])
def repo(request: pytest.FixtureRequest) -> Generator[TagRepositoryInterface, None, None]:
    if request.param == "inmemory":
        yield InMemoryTagRepository()
        return
    engine = create_engine("sqlite:///:memory:")
    executor = SqlAlchemyQueryExecutor(engine)
    _create_schema(executor)
    yield SqlAlchemyTagRepository(executor)
    engine.dispose()


def test_save_and_find_by_id(repo: TagRepositoryInterface) -> None:
    tag = repo.save("python")
    found = repo.find_by_id(tag.id)
    assert found == tag


def test_find_by_id_returns_none_when_missing(repo: TagRepositoryInterface) -> None:
    assert repo.find_by_id(9999) is None


def test_find_all_returns_saved_tags(repo: TagRepositoryInterface) -> None:
    repo.save("python")
    repo.save("fastapi")
    items = repo.find_all(limit=10, offset=0)
    assert len(items) == 2


def test_find_all_respects_limit_and_offset(repo: TagRepositoryInterface) -> None:
    for name in ["a", "b", "c", "d", "e"]:
        repo.save(name)
    page = repo.find_all(limit=2, offset=2)
    assert len(page) == 2


def test_count_reflects_saved_tags(repo: TagRepositoryInterface) -> None:
    assert repo.count() == 0
    repo.save("x")
    repo.save("y")
    assert repo.count() == 2


def test_update_changes_name(repo: TagRepositoryInterface) -> None:
    tag = repo.save("old")
    updated = repo.update(tag.id, "new")
    assert updated == Tag(id=tag.id, name="new")


def test_update_returns_none_for_missing_id(repo: TagRepositoryInterface) -> None:
    assert repo.update(9999, "x") is None


def test_delete_removes_tag(repo: TagRepositoryInterface) -> None:
    tag = repo.save("temp")
    assert repo.delete(tag.id) is True
    assert repo.find_by_id(tag.id) is None


def test_delete_returns_false_for_missing_id(repo: TagRepositoryInterface) -> None:
    assert repo.delete(9999) is False
