# MCP setup guide — Claude Desktop integration

## Overview

`example/mcp.py` exposes all Note, Tag, and Comment UseCases (15 tools) as MCP tools.
Once configured, Claude Desktop and the `claude` CLI can perform CRUD operations directly.

## Prerequisites

- `uv sync` completed
- Python 3.12+ environment

## Claude Desktop configuration

`claude_desktop_config.json` is located at:

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

### macOS / Linux (native)

```json
{
  "mcpServers": {
    "nene2-example": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/nene2-python",
        "run",
        "python",
        "-m",
        "example.mcp"
      ],
      "env": {
        "DB_ADAPTER": "sqlite",
        "DB_NAME": "/path/to/nene2-python/data/nene2.db"
      }
    }
  }
}
```

Replace `/path/to/nene2-python` with the absolute path to this repository.

### Windows + WSL2

Claude Desktop runs on Windows but the project lives inside WSL2.
Use `wsl` as the command to bridge them:

```json
{
  "mcpServers": {
    "nene2-example": {
      "command": "wsl",
      "args": [
        "-e", "bash", "-c",
        "cd /home/<user>/nene2-python && PYTHONPATH=src uv run python -m example.mcp"
      ],
      "env": {
        "DB_ADAPTER": "sqlite",
        "DB_NAME": "/home/<user>/nene2-python/data/nene2.db"
      }
    }
  }
}
```

> All paths must be **WSL Linux paths** (e.g. `/home/user/...`), not Windows paths.
> The `DB_NAME` must also be a Linux path so SQLite creates the file inside WSL.

For a project installed via `uv add git+...` (not the nene2-python repo itself):

```json
{
  "mcpServers": {
    "myapp": {
      "command": "wsl",
      "args": [
        "-e", "bash", "-c",
        "cd /home/<user>/my-project && PYTHONPATH=src uv run python -m mcp_server"
      ]
    }
  }
}
```

## Available tools

| Tool | Description |
|---|---|
| `list_notes` | List notes with pagination |
| `get_note` | Get a note by ID |
| `create_note` | Create a new note |
| `update_note` | Update a note |
| `delete_note` | Delete a note |
| `list_tags` | List tags |
| `get_tag` | Get a tag by ID |
| `create_tag` | Create a new tag |
| `update_tag` | Update a tag |
| `delete_tag` | Delete a tag |
| `list_comments` | List comments on a note |
| `get_comment` | Get a comment by ID |
| `create_comment` | Create a comment on a note |
| `update_comment` | Update a comment |
| `delete_comment` | Delete a comment |

## Running via CLI

```bash
uv run python -m example.mcp
```

The server listens on stdin/stdout (stdio transport) — standard for MCP.

## Custom transport

```python
from example.mcp import create_mcp_server

server = create_mcp_server()
server.run(transport="sse")          # Server-Sent Events
server.run(transport="streamable-http")  # HTTP streaming
```

---

## Sharing state between MCP server and HTTP API

The MCP server runs as a **separate process** from the HTTP API.
`InMemoryXxxRepository` creates its own isolated store per process —
data written via MCP is not visible to the HTTP API, and vice versa.

To share state, point both processes at the same persistent database:

**HTTP API `.env`**:

```dotenv
DB_ADAPTER=sqlite
DB_NAME=/absolute/path/to/shared.db
```

**Claude Desktop `claude_desktop_config.json`**:

```json
"env": {
  "DB_ADAPTER": "sqlite",
  "DB_NAME": "/absolute/path/to/shared.db"
}
```

Both processes open the same SQLite file via SQLAlchemy.
SQLite's WAL mode handles concurrent reads safely for light workloads.

> For high-concurrency production use, prefer MySQL or PostgreSQL.
