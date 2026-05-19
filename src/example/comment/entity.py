"""Comment domain entity."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Comment:
    id: int
    note_id: int
    body: str
