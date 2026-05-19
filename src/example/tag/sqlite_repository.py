"""SQLite-backed Tag repository using SQLAlchemy Core."""

from nene2.database import DatabaseQueryExecutorInterface

from .entity import Tag
from .repository import TagRepositoryInterface


class SqliteTagRepository(TagRepositoryInterface):
    """Persistent Tag repository backed by a SQL database via SQLAlchemy Core."""

    def __init__(self, executor: DatabaseQueryExecutorInterface) -> None:
        self._executor = executor

    def find_all(self, limit: int, offset: int) -> list[Tag]:
        rows = self._executor.fetch_all(
            "SELECT id, name FROM tags ORDER BY id LIMIT :limit OFFSET :offset",
            {"limit": limit, "offset": offset},
        )
        return [Tag(id=row["id"], name=row["name"]) for row in rows]

    def find_by_id(self, tag_id: int) -> Tag | None:
        row = self._executor.fetch_one(
            "SELECT id, name FROM tags WHERE id = :id",
            {"id": tag_id},
        )
        return Tag(id=row["id"], name=row["name"]) if row else None

    def save(self, name: str) -> Tag:
        new_id = self._executor.write(
            "INSERT INTO tags (name) VALUES (:name)",
            {"name": name},
        )
        return Tag(id=new_id, name=name)

    def update(self, tag_id: int, name: str) -> Tag | None:
        affected = self._executor.write(
            "UPDATE tags SET name = :name WHERE id = :id",
            {"name": name, "id": tag_id},
        )
        return Tag(id=tag_id, name=name) if affected > 0 else None

    def delete(self, tag_id: int) -> bool:
        affected = self._executor.write(
            "DELETE FROM tags WHERE id = :id",
            {"id": tag_id},
        )
        return affected > 0

    def count(self) -> int:
        row = self._executor.fetch_one("SELECT COUNT(*) AS cnt FROM tags")
        return int(row["cnt"]) if row else 0
