# ADR-0009 — MCP Integration Design

Date: 2026-05-19  
Status: Accepted

## Context

UseCase objects contain all business logic and are already independent of HTTP. Exposing them as MCP tools allows AI agents (Claude Desktop, claude CLI, any MCP client) to call them directly without the HTTP stack.

## Decision

- **`mcp>=1.0` (Anthropic official Python SDK)** as the transport layer
- **`FastMCP`** from `mcp.server.fastmcp` for tool declaration via decorators
- **`LocalMcpServer`** in `nene2.mcp` — thin wrapper with NENE2 naming and `stdio` default
- **Tool registration in application layer** (`example/mcp.py`), not in the framework
- **`_build_repositories()`** from `example/app.py` is reused — same DB config, same SQLite/MySQL support
- **`dataclasses.asdict()`** serializes entity output to `dict` for MCP JSON transport
- **`python -m example`** or **`python -m example.mcp`** as the entry point
- **`stdio` transport** by default (Claude Desktop integration); `sse` / `streamable-http` available for web clients

## Tool naming

| MCP tool | UseCase |
|---|---|
| `list_notes` | `ListNotesUseCase` |
| `get_note` | `GetNoteUseCase` |
| `create_note` | `CreateNoteUseCase` |
| `update_note` | `UpdateNoteUseCase` |
| `delete_note` | `DeleteNoteUseCase` |
| `list_tags` | `ListTagsUseCase` |
| `get_tag` | `GetTagUseCase` |
| `create_tag` | `CreateTagUseCase` |
| `update_tag` | `UpdateTagUseCase` |
| `delete_tag` | `DeleteTagUseCase` |

## Consequences

- Zero additional API surface — each tool maps 1:1 to an existing UseCase
- Domain exceptions (`NoteNotFoundException`) propagate as MCP error responses automatically
- No auth on the MCP server itself (Claude Desktop is local-only); add `TokenVerifierProtocol` wrapping if exposing via `sse` transport
- MCP server and HTTP server share the same DB (same `_build_repositories()` call) — data is consistent
