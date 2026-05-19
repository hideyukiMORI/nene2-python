"""Tag repository interface and in-memory implementation."""

from abc import ABC, abstractmethod

from .entity import Tag


class TagRepositoryInterface(ABC):
    @abstractmethod
    def find_all(self, limit: int, offset: int) -> list[Tag]: ...

    @abstractmethod
    def find_by_id(self, tag_id: int) -> Tag | None: ...

    @abstractmethod
    def save(self, name: str) -> Tag: ...

    @abstractmethod
    def update(self, tag_id: int, name: str) -> Tag | None: ...

    @abstractmethod
    def delete(self, tag_id: int) -> bool: ...

    @abstractmethod
    def count(self) -> int: ...


class InMemoryTagRepository(TagRepositoryInterface):
    """In-memory implementation for development and testing."""

    def __init__(self) -> None:
        self._store: dict[int, Tag] = {}
        self._next_id: int = 1

    def find_all(self, limit: int, offset: int) -> list[Tag]:
        tags = sorted(self._store.values(), key=lambda t: t.id)
        return tags[offset : offset + limit]

    def find_by_id(self, tag_id: int) -> Tag | None:
        return self._store.get(tag_id)

    def save(self, name: str) -> Tag:
        tag = Tag(id=self._next_id, name=name)
        self._store[self._next_id] = tag
        self._next_id += 1
        return tag

    def update(self, tag_id: int, name: str) -> Tag | None:
        if tag_id not in self._store:
            return None
        updated = Tag(id=tag_id, name=name)
        self._store[tag_id] = updated
        return updated

    def delete(self, tag_id: int) -> bool:
        if tag_id not in self._store:
            return False
        del self._store[tag_id]
        return True

    def count(self) -> int:
        return len(self._store)
