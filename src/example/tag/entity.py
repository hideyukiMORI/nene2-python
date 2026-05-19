"""Tag domain entity."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Tag:
    id: int
    name: str
