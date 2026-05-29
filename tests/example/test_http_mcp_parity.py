"""Executable proof of the NENE2 differentiator: one UseCase, two surfaces.

The same domain UseCase (`CreateNoteUseCase`, `GetNoteUseCase`, …) is what the HTTP
handler calls *and* what the MCP tool calls — domain logic is written once and
delivered over both surfaces. These tests wire an HTTP app and an MCP server onto
the *same* SQLite database and assert the surfaces are interchangeable: write
through one, read through the other.

What is intentionally *not* shared is the HTTP boundary (Pydantic body validation,
auth, pagination parsing) — that lives in the thin HTTP layer, not the UseCase.
See docs/explanation/one-usecase-two-surfaces.md.
"""

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from example.app import create_app
from example.mcp import create_mcp_server
from nene2.config import AppSettings
from nene2.mcp import LocalMcpServer


@pytest.fixture
def settings(tmp_path: Path) -> AppSettings:
    # A real on-disk SQLite file so the HTTP app and the MCP server — each building
    # its own engine — share one store, exactly as they would in production.
    db_path = tmp_path / "parity.db"
    return AppSettings(db_adapter="sqlite", db_name=str(db_path), throttle_enabled=False)


@pytest.fixture
def http(settings: AppSettings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def mcp(settings: AppSettings) -> LocalMcpServer:
    return create_mcp_server(settings)


def _mcp_blocks(server: LocalMcpServer, name: str, arguments: dict[str, Any]) -> list[Any]:
    # FastMCP returns one content block per returned item, so a list-returning tool
    # yields several blocks. Parse them all; callers pick one or the whole list.
    raw = asyncio.run(server._mcp.call_tool(name, arguments))  # noqa: SLF001
    content = raw[0] if isinstance(raw, tuple) else raw
    return [json.loads(block.text) for block in content]


def _mcp_one(server: LocalMcpServer, name: str, arguments: dict[str, Any]) -> Any:
    return _mcp_blocks(server, name, arguments)[0]


def test_note_written_via_mcp_is_readable_via_http(http: TestClient, mcp: LocalMcpServer) -> None:
    created = _mcp_one(mcp, "create_note", {"title": "from MCP", "body": "x"})
    response = http.get(f"/examples/notes/{created['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "from MCP"


def test_note_written_via_http_is_readable_via_mcp(http: TestClient, mcp: LocalMcpServer) -> None:
    note_id = http.post("/examples/notes", json={"title": "from HTTP", "body": "y"}).json()["id"]
    fetched = _mcp_one(mcp, "get_note", {"note_id": note_id})
    assert fetched["title"] == "from HTTP"


def test_both_surfaces_share_one_store(http: TestClient, mcp: LocalMcpServer) -> None:
    _mcp_one(mcp, "create_note", {"title": "a", "body": "a"})
    http.post("/examples/notes", json={"title": "b", "body": "b"})
    listed = _mcp_blocks(mcp, "list_notes", {})
    assert len(listed) == 2
