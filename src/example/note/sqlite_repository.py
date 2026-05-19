"""SQLite-backed Note repository using SQLAlchemy Core."""

from nene2.database import DatabaseQueryExecutorInterface

from .entity import Note
from .repository import NoteRepositoryInterface


class SqliteNoteRepository(NoteRepositoryInterface):
    """Persistent Note repository backed by a SQL database via SQLAlchemy Core."""

    def __init__(self, executor: DatabaseQueryExecutorInterface) -> None:
        self._executor = executor

    def find_all(self, limit: int, offset: int) -> list[Note]:
        rows = self._executor.fetch_all(
            "SELECT id, title, body FROM notes ORDER BY id LIMIT :limit OFFSET :offset",
            {"limit": limit, "offset": offset},
        )
        return [Note(id=row["id"], title=row["title"], body=row["body"]) for row in rows]

    def find_by_id(self, note_id: int) -> Note | None:
        row = self._executor.fetch_one(
            "SELECT id, title, body FROM notes WHERE id = :id",
            {"id": note_id},
        )
        return Note(id=row["id"], title=row["title"], body=row["body"]) if row else None

    def save(self, title: str, body: str) -> Note:
        new_id = self._executor.write(
            "INSERT INTO notes (title, body) VALUES (:title, :body)",
            {"title": title, "body": body},
        )
        return Note(id=new_id, title=title, body=body)

    def update(self, note_id: int, title: str, body: str) -> Note | None:
        affected = self._executor.write(
            "UPDATE notes SET title = :title, body = :body WHERE id = :id",
            {"title": title, "body": body, "id": note_id},
        )
        return Note(id=note_id, title=title, body=body) if affected > 0 else None

    def delete(self, note_id: int) -> bool:
        affected = self._executor.write(
            "DELETE FROM notes WHERE id = :id",
            {"id": note_id},
        )
        return affected > 0

    def count(self) -> int:
        row = self._executor.fetch_one("SELECT COUNT(*) AS cnt FROM notes")
        return int(row["cnt"]) if row else 0
