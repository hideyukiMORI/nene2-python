"""Note domain entity."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Note:
    id: int
    title: str
    body: str
