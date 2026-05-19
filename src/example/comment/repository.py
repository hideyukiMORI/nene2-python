"""Comment repository interface and in-memory implementation."""

from abc import ABC, abstractmethod

from .entity import Comment


class CommentRepositoryInterface(ABC):
    @abstractmethod
    def find_all_by_note(self, note_id: int, limit: int, offset: int) -> list[Comment]: ...

    @abstractmethod
    def find_by_id(self, comment_id: int) -> Comment | None: ...

    @abstractmethod
    def save(self, note_id: int, body: str) -> Comment: ...

    @abstractmethod
    def update(self, comment_id: int, body: str) -> Comment | None: ...

    @abstractmethod
    def delete(self, comment_id: int) -> bool: ...

    @abstractmethod
    def count_by_note(self, note_id: int) -> int: ...


class InMemoryCommentRepository(CommentRepositoryInterface):
    def __init__(self) -> None:
        self._store: dict[int, Comment] = {}
        self._next_id = 1

    def find_all_by_note(self, note_id: int, limit: int, offset: int) -> list[Comment]:
        items = sorted(
            (c for c in self._store.values() if c.note_id == note_id), key=lambda c: c.id
        )
        return items[offset : offset + limit]

    def find_by_id(self, comment_id: int) -> Comment | None:
        return self._store.get(comment_id)

    def save(self, note_id: int, body: str) -> Comment:
        comment = Comment(id=self._next_id, note_id=note_id, body=body)
        self._store[self._next_id] = comment
        self._next_id += 1
        return comment

    def update(self, comment_id: int, body: str) -> Comment | None:
        existing = self._store.get(comment_id)
        if existing is None:
            return None
        updated = Comment(id=existing.id, note_id=existing.note_id, body=body)
        self._store[comment_id] = updated
        return updated

    def delete(self, comment_id: int) -> bool:
        if comment_id not in self._store:
            return False
        del self._store[comment_id]
        return True

    def count_by_note(self, note_id: int) -> int:
        return sum(1 for c in self._store.values() if c.note_id == note_id)
