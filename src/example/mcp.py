"""MCP server factory — registers Note, Tag, and Comment UseCases as MCP tools.

Run with:  uv run python -m example.mcp
Configure in Claude Desktop: see docs/howto/mcp-setup.md
"""

from dataclasses import asdict

from nene2.config import AppSettings
from nene2.mcp import LocalMcpServer

from .app import _build_repositories
from .comment.use_case import (
    CreateCommentInput,
    CreateCommentUseCase,
    DeleteCommentInput,
    DeleteCommentUseCase,
    GetCommentInput,
    GetCommentUseCase,
    ListCommentsInput,
    ListCommentsUseCase,
    UpdateCommentInput,
    UpdateCommentUseCase,
)
from .note.use_case import (
    CreateNoteInput,
    CreateNoteUseCase,
    DeleteNoteInput,
    DeleteNoteUseCase,
    GetNoteInput,
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
    GetTagInput,
    GetTagUseCase,
    ListTagsInput,
    ListTagsUseCase,
    UpdateTagInput,
    UpdateTagUseCase,
)


def create_mcp_server(settings: AppSettings | None = None) -> LocalMcpServer:
    """Wire repositories and register all tools. Returns a runnable server."""
    cfg = settings or AppSettings()
    note_repo, tag_repo, comment_repo, _ = _build_repositories(cfg)

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

    comment_list = ListCommentsUseCase(comment_repo)
    comment_get = GetCommentUseCase(comment_repo)
    comment_create = CreateCommentUseCase(comment_repo, note_repo)
    comment_update = UpdateCommentUseCase(comment_repo)
    comment_delete = DeleteCommentUseCase(comment_repo)

    server = LocalMcpServer(
        "nene2-example",
        instructions="Note, Tag, and Comment management API for the NENE2 example app.",
    )

    @server.tool("List notes with optional pagination.")
    def list_notes(limit: int = 20, offset: int = 0) -> list[dict]:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        result = note_list.execute(ListNotesInput(limit=limit, offset=offset))
        return [asdict(n) for n in result.items]

    @server.tool("Get a single note by ID.")
    def get_note(note_id: int) -> dict:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        return asdict(note_get.execute(GetNoteInput(note_id=note_id)))

    @server.tool("Create a new note.")
    def create_note(title: str, body: str) -> dict:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        return asdict(note_create.execute(CreateNoteInput(title=title, body=body)))

    @server.tool("Update an existing note.")
    def update_note(note_id: int, title: str, body: str) -> dict:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        return asdict(note_update.execute(UpdateNoteInput(note_id=note_id, title=title, body=body)))

    @server.tool("Delete a note by ID.")
    def delete_note(note_id: int) -> dict:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        note_delete.execute(DeleteNoteInput(note_id=note_id))
        return {"deleted": True, "note_id": note_id}

    @server.tool("List tags with optional pagination.")
    def list_tags(limit: int = 20, offset: int = 0) -> list[dict]:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        result = tag_list.execute(ListTagsInput(limit=limit, offset=offset))
        return [asdict(t) for t in result.items]

    @server.tool("Get a single tag by ID.")
    def get_tag(tag_id: int) -> dict:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        return asdict(tag_get.execute(GetTagInput(tag_id=tag_id)))

    @server.tool("Create a new tag.")
    def create_tag(name: str) -> dict:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        return asdict(tag_create.execute(CreateTagInput(name=name)))

    @server.tool("Update an existing tag.")
    def update_tag(tag_id: int, name: str) -> dict:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        return asdict(tag_update.execute(UpdateTagInput(tag_id=tag_id, name=name)))

    @server.tool("Delete a tag by ID.")
    def delete_tag(tag_id: int) -> dict:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        tag_delete.execute(DeleteTagInput(tag_id=tag_id))
        return {"deleted": True, "tag_id": tag_id}

    @server.tool("List comments for a note.")
    def list_comments(note_id: int, limit: int = 20, offset: int = 0) -> list[dict]:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        result = comment_list.execute(
            ListCommentsInput(note_id=note_id, limit=limit, offset=offset)
        )
        return [asdict(c) for c in result.items]

    @server.tool("Get a single comment by ID.")
    def get_comment(comment_id: int) -> dict:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        return asdict(comment_get.execute(GetCommentInput(comment_id=comment_id)))

    @server.tool("Create a new comment on a note.")
    def create_comment(note_id: int, body: str) -> dict:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        return asdict(comment_create.execute(CreateCommentInput(note_id=note_id, body=body)))

    @server.tool("Update an existing comment.")
    def update_comment(comment_id: int, body: str) -> dict:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        return asdict(comment_update.execute(UpdateCommentInput(comment_id=comment_id, body=body)))

    @server.tool("Delete a comment by ID.")
    def delete_comment(comment_id: int) -> dict:  # type: ignore[type-arg]  # reason: mcp tool handler type stubs do not support generic dict
        comment_delete.execute(DeleteCommentInput(comment_id=comment_id))
        return {"deleted": True, "comment_id": comment_id}

    return server
