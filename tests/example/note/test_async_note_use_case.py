"""Async Note use-case tests — validates AsyncUseCaseProtocol integration."""

import pytest

from example.note.async_use_case import (
    AsyncGetNoteInput,
    AsyncGetNoteUseCase,
    AsyncListNotesUseCase,
)
from example.note.exceptions import NoteNotFoundException
from example.note.repository import InMemoryNoteRepository
from example.note.use_case import CreateNoteInput, CreateNoteUseCase, ListNotesInput


@pytest.fixture()
def repo() -> InMemoryNoteRepository:
    return InMemoryNoteRepository()


async def test_async_list_returns_empty_when_no_notes(
    repo: InMemoryNoteRepository,
) -> None:
    result = await AsyncListNotesUseCase(repo).execute(ListNotesInput(limit=10, offset=0))
    assert result.total == 0
    assert result.items == []


async def test_async_list_returns_created_notes(repo: InMemoryNoteRepository) -> None:
    CreateNoteUseCase(repo).execute(CreateNoteInput(title="t1", body="b1"))
    CreateNoteUseCase(repo).execute(CreateNoteInput(title="t2", body="b2"))
    result = await AsyncListNotesUseCase(repo).execute(ListNotesInput(limit=10, offset=0))
    assert result.total == 2


async def test_async_get_returns_note(repo: InMemoryNoteRepository) -> None:
    note = CreateNoteUseCase(repo).execute(CreateNoteInput(title="hello", body="world"))
    fetched = await AsyncGetNoteUseCase(repo).execute(AsyncGetNoteInput(note_id=note.id))
    assert fetched == note


async def test_async_get_raises_when_not_found(repo: InMemoryNoteRepository) -> None:
    with pytest.raises(NoteNotFoundException):
        await AsyncGetNoteUseCase(repo).execute(AsyncGetNoteInput(note_id=9999))
