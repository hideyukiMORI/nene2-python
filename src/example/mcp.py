"""MCP server factory — registers Note and Tag UseCases as MCP tools.

Run with:  uv run python -m example.mcp
Configure in Claude Desktop: see docs/howto/mcp-setup.md
"""

from dataclasses import asdict

from nene2.config import AppSettings
from nene2.mcp import LocalMcpServer

from .app import _build_repositories
from .note.use_case import (
    CreateNoteInput,
    CreateNoteUseCase,
    DeleteNoteInput,
    DeleteNoteUseCase,
    GetNoteUseCase,
    ListNotesInput,
    ListNotesUseCase,
    UpdateNoteInput,
    UpdateNoteUseCase,
)
from .tag.use_case import (
    CreateTagInput,
    CreateTagUseCase,
    DeleteTagInput,
    DeleteTagUseCase,
    GetTagUseCase,
    ListTagsInput,
    ListTagsUseCase,
    UpdateTagInput,
    UpdateTagUseCase,
)


def create_mcp_server(settings: AppSettings | None = None) -> LocalMcpServer:
    """Wire repositories and register all tools. Returns a runnable server."""
    cfg = settings or AppSettings()
    note_repo, tag_repo, _ = _build_repositories(cfg)

    note_list = ListNotesUseCase(note_repo)
    note_get = GetNoteUseCase(note_repo)
    note_create = CreateNoteUseCase(note_repo)
    note_update = UpdateNoteUseCase(note_repo)
    note_delete = DeleteNoteUseCase(note_repo)

    tag_list = ListTagsUseCase(tag_repo)
    tag_get = GetTagUseCase(tag_repo)
    tag_create = CreateTagUseCase(tag_repo)
    tag_update = UpdateTagUseCase(tag_repo)
    tag_delete = DeleteTagUseCase(tag_repo)

    server = LocalMcpServer(
        "nene2-example",
        instructions="Note and Tag management API for the NENE2 example app.",
    )

    @server.tool("List notes with optional pagination.")
    def list_notes(limit: int = 20, offset: int = 0) -> list[dict]:  # type: ignore[type-arg]
        result = note_list.execute(ListNotesInput(limit=limit, offset=offset))
        return [asdict(n) for n in result.items]

    @server.tool("Get a single note by ID.")
    def get_note(note_id: int) -> dict:  # type: ignore[type-arg]
        return asdict(note_get.execute(note_id))

    @server.tool("Create a new note.")
    def create_note(title: str, body: str) -> dict:  # type: ignore[type-arg]
        return asdict(note_create.execute(CreateNoteInput(title=title, body=body)))

    @server.tool("Update an existing note.")
    def update_note(note_id: int, title: str, body: str) -> dict:  # type: ignore[type-arg]
        return asdict(note_update.execute(UpdateNoteInput(note_id=note_id, title=title, body=body)))

    @server.tool("Delete a note by ID.")
    def delete_note(note_id: int) -> dict:  # type: ignore[type-arg]
        note_delete.execute(DeleteNoteInput(note_id=note_id))
        return {"deleted": True, "note_id": note_id}

    @server.tool("List tags with optional pagination.")
    def list_tags(limit: int = 20, offset: int = 0) -> list[dict]:  # type: ignore[type-arg]
        result = tag_list.execute(ListTagsInput(limit=limit, offset=offset))
        return [asdict(t) for t in result.items]

    @server.tool("Get a single tag by ID.")
    def get_tag(tag_id: int) -> dict:  # type: ignore[type-arg]
        return asdict(tag_get.execute(tag_id))

    @server.tool("Create a new tag.")
    def create_tag(name: str) -> dict:  # type: ignore[type-arg]
        return asdict(tag_create.execute(CreateTagInput(name=name)))

    @server.tool("Update an existing tag.")
    def update_tag(tag_id: int, name: str) -> dict:  # type: ignore[type-arg]
        return asdict(tag_update.execute(UpdateTagInput(tag_id=tag_id, name=name)))

    @server.tool("Delete a tag by ID.")
    def delete_tag(tag_id: int) -> dict:  # type: ignore[type-arg]
        tag_delete.execute(DeleteTagInput(tag_id=tag_id))
        return {"deleted": True, "tag_id": tag_id}

    return server
