"""Async Note use-cases — demonstrates AsyncUseCaseProtocol with asyncio.

Sync repositories are wrapped with asyncio.to_thread so the event loop
is never blocked. asyncio.gather enables concurrent repo calls.
"""

import asyncio
from dataclasses import dataclass

from .entity import Note
from .exceptions import NoteNotFoundException
from .repository import NoteRepositoryInterface
from .use_case import ListNotesInput, ListNotesOutput


class AsyncListNotesUseCase:
    """Lists notes; runs find_all and count concurrently via asyncio.gather."""

    def __init__(self, repository: NoteRepositoryInterface) -> None:
        self._repository = repository

    async def execute(self, input_: ListNotesInput) -> ListNotesOutput:
        items, total = await asyncio.gather(
            asyncio.to_thread(self._repository.find_all, input_.limit, input_.offset),
            asyncio.to_thread(self._repository.count),
        )
        return ListNotesOutput(
            items=items,
            limit=input_.limit,
            offset=input_.offset,
            total=total,
        )


@dataclass(frozen=True, slots=True)
class AsyncGetNoteInput:
    note_id: int


class AsyncGetNoteUseCase:
    """Fetches a single note asynchronously."""

    def __init__(self, repository: NoteRepositoryInterface) -> None:
        self._repository = repository

    async def execute(self, input_: AsyncGetNoteInput) -> Note:
        note = await asyncio.to_thread(self._repository.find_by_id, input_.note_id)
        if note is None:
            raise NoteNotFoundException(input_.note_id)
        return note
