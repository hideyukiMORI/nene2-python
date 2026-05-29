# MCP 设置指南 — Claude Desktop 集成

## 概述

`example/mcp.py` 将所有 Note、Tag 和 Comment UseCase（15 个工具）作为 MCP 工具暴露。配置完成后，Claude Desktop 和 `claude` CLI 可以直接执行 CRUD 操作。

## 前提条件

- 已完成 `uv sync`
- Python 3.12+ 环境

## Claude Desktop 配置

`claude_desktop_config.json` 的位置：

| 操作系统 | 路径 |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

### macOS / Linux（原生）

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

将 `/path/to/nene2-python` 替换为本仓库的绝对路径。

### Windows + WSL2

Claude Desktop 运行在 Windows 上，但项目位于 WSL2 内。使用 `wsl` 命令桥接两者：

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

> 所有路径必须使用 **WSL Linux 路径**（如 `/home/user/...`），而非 Windows 路径。`DB_NAME` 也必须是 Linux 路径，以便 SQLite 在 WSL 内创建文件。

对于通过 `uv add git+...` 安装的项目（而非 nene2-python 仓库本身）：

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

## 可用工具

| 工具 | 描述 |
|---|---|
| `list_notes` | 分页获取笔记列表 |
| `get_note` | 按 ID 获取笔记 |
| `create_note` | 创建新笔记 |
| `update_note` | 更新笔记 |
| `delete_note` | 删除笔记 |
| `list_tags` | 获取标签列表 |
| `get_tag` | 按 ID 获取标签 |
| `create_tag` | 创建新标签 |
| `update_tag` | 更新标签 |
| `delete_tag` | 删除标签 |
| `list_comments` | 获取笔记的评论列表 |
| `get_comment` | 按 ID 获取评论 |
| `create_comment` | 在笔记下创建评论 |
| `update_comment` | 更新评论 |
| `delete_comment` | 删除评论 |

## 通过 CLI 运行

```bash
uv run python -m example.mcp
```

服务器监听 stdin/stdout（stdio 传输）— 这是 MCP 的标准方式。

## 自定义传输

```python
from example.mcp import create_mcp_server

server = create_mcp_server()
server.run(transport="sse")          # Server-Sent Events
server.run(transport="streamable-http")  # HTTP 流式传输
```

---

## 在 MCP 服务器和 HTTP API 之间共享状态

MCP 服务器作为与 HTTP API **独立的进程**运行。`InMemoryXxxRepository` 为每个进程创建独立的存储 — 通过 MCP 写入的数据对 HTTP API 不可见，反之亦然。

若要共享状态，将两个进程指向同一个持久化数据库：

**HTTP API `.env`**：

```dotenv
DB_ADAPTER=sqlite
DB_NAME=/absolute/path/to/shared.db
```

**Claude Desktop `claude_desktop_config.json`**：

```json
"env": {
  "DB_ADAPTER": "sqlite",
  "DB_NAME": "/absolute/path/to/shared.db"
}
```

两个进程通过 SQLAlchemy 打开同一个 SQLite 文件。SQLite 的 WAL 模式可以安全地处理轻量级工作负载下的并发读取。

> 对于高并发生产环境，建议使用 MySQL 或 PostgreSQL。
