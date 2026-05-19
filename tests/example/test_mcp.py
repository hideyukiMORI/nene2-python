"""Tests for the MCP server factory (example/mcp.py).

Tests exercise tool registration and basic tool behavior using in-memory
repositories — no network or stdio involved.
"""

from example.mcp import create_mcp_server
from example.note.repository import InMemoryNoteRepository
from example.note.use_case import (
    CreateNoteInput,
    CreateNoteUseCase,
    DeleteNoteInput,
    DeleteNoteUseCase,
    GetNoteInput,
    GetNoteUseCase,
    ListNotesInput,
    ListNotesUseCase,
)
from nene2.config import AppSettings
from nene2.mcp import LocalMcpServer


def _settings() -> AppSettings:
    return AppSettings(db_adapter="sqlite", db_name=":memory:", throttle_enabled=False)


def test_create_mcp_server_returns_server() -> None:
    server = create_mcp_server(_settings())
    assert isinstance(server, LocalMcpServer)


def test_note_create_use_case() -> None:
    repo = InMemoryNoteRepository()
    note = CreateNoteUseCase(repo).execute(CreateNoteInput(title="hello", body="world"))
    assert note.id == 1
    assert note.title == "hello"


def test_note_lifecycle_via_use_cases() -> None:
    repo = InMemoryNoteRepository()
    create_uc = CreateNoteUseCase(repo)
    list_uc = ListNotesUseCase(repo)
    get_uc = GetNoteUseCase(repo)
    delete_uc = DeleteNoteUseCase(repo)

    note = create_uc.execute(CreateNoteInput(title="MCP note", body="content"))
    assert list_uc.execute(ListNotesInput(limit=10, offset=0)).total == 1
    fetched = get_uc.execute(GetNoteInput(note_id=note.id))
    assert fetched.title == "MCP note"
    delete_uc.execute(DeleteNoteInput(note_id=note.id))
    assert list_uc.execute(ListNotesInput(limit=10, offset=0)).total == 0
