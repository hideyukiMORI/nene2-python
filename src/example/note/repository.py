"""Note repository interface and in-memory implementation."""

from abc import ABC, abstractmethod

from .entity import Note


class NoteRepositoryInterface(ABC):
    @abstractmethod
    def find_all(self, limit: int, offset: int) -> list[Note]: ...

    @abstractmethod
    def find_by_id(self, note_id: int) -> Note | None: ...

    @abstractmethod
    def save(self, title: str, body: str) -> Note: ...

    @abstractmethod
    def count(self) -> int: ...


class InMemoryNoteRepository(NoteRepositoryInterface):
    """In-memory implementation for development and testing."""

    def __init__(self) -> None:
        self._store: dict[int, Note] = {}
        self._next_id: int = 1

    def find_all(self, limit: int, offset: int) -> list[Note]:
        notes = sorted(self._store.values(), key=lambda n: n.id)
        return notes[offset : offset + limit]

    def find_by_id(self, note_id: int) -> Note | None:
        return self._store.get(note_id)

    def save(self, title: str, body: str) -> Note:
        note = Note(id=self._next_id, title=title, body=body)
        self._store[self._next_id] = note
        self._next_id += 1
        return note

    def count(self) -> int:
        return len(self._store)
