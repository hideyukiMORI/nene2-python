"""SQL-backed Comment repository using SQLAlchemy Core."""

from nene2.database import DatabaseQueryExecutorInterface

from .entity import Comment
from .repository import CommentRepositoryInterface


class SqlAlchemyCommentRepository(CommentRepositoryInterface):
    """Persistent Comment repository backed by any SQLAlchemy-supported database."""

    def __init__(self, executor: DatabaseQueryExecutorInterface) -> None:
        self._executor = executor

    def find_all_by_note(self, note_id: int, limit: int, offset: int) -> list[Comment]:
        rows = self._executor.fetch_all(
            "SELECT id, note_id, body FROM comments"
            " WHERE note_id = :note_id ORDER BY id LIMIT :limit OFFSET :offset",
            {"note_id": note_id, "limit": limit, "offset": offset},
        )
        return [Comment(id=r["id"], note_id=r["note_id"], body=r["body"]) for r in rows]

    def find_by_id(self, comment_id: int) -> Comment | None:
        row = self._executor.fetch_one(
            "SELECT id, note_id, body FROM comments WHERE id = :id",
            {"id": comment_id},
        )
        return Comment(id=row["id"], note_id=row["note_id"], body=row["body"]) if row else None

    def save(self, note_id: int, body: str) -> Comment:
        new_id = self._executor.write(
            "INSERT INTO comments (note_id, body) VALUES (:note_id, :body)",
            {"note_id": note_id, "body": body},
        )
        return Comment(id=new_id, note_id=note_id, body=body)

    def update(self, comment_id: int, body: str) -> Comment | None:
        row = self._executor.fetch_one(
            "SELECT note_id FROM comments WHERE id = :id", {"id": comment_id}
        )
        if row is None:
            return None
        self._executor.write(
            "UPDATE comments SET body = :body WHERE id = :id",
            {"body": body, "id": comment_id},
        )
        return Comment(id=comment_id, note_id=row["note_id"], body=body)

    def delete(self, comment_id: int) -> bool:
        affected = self._executor.write(
            "DELETE FROM comments WHERE id = :id", {"id": comment_id}
        )
        return affected > 0

    def count_by_note(self, note_id: int) -> int:
        row = self._executor.fetch_one(
            "SELECT COUNT(*) AS cnt FROM comments WHERE note_id = :note_id",
            {"note_id": note_id},
        )
        return int(row["cnt"]) if row else 0
