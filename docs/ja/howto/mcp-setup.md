# MCP セットアップガイド — Claude Desktop 連携

## 概要

`example/mcp.py` は Note・Tag・Comment の全 UseCase（15 ツール）を MCP ツールとして公開します。
Claude Desktop や `claude` CLI から直接 CRUD 操作が可能になります。

## 前提

- `uv sync` 完了済み
- Python 3.12+ 環境

## Claude Desktop への設定

`claude_desktop_config.json` に以下を追加します:

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

`/path/to/nene2-python` をリポジトリの絶対パスに変更してください。

## 利用可能なツール

| ツール | 説明 |
|---|---|
| `list_notes` | Note 一覧取得（ページネーション付き） |
| `get_note` | ID 指定で Note を取得 |
| `create_note` | Note を作成 |
| `update_note` | Note を更新 |
| `delete_note` | Note を削除 |
| `list_tags` | Tag 一覧取得 |
| `get_tag` | ID 指定で Tag を取得 |
| `create_tag` | Tag を作成 |
| `update_tag` | Tag を更新 |
| `delete_tag` | Tag を削除 |
| `list_comments` | Note に紐づくコメント一覧 |
| `get_comment` | ID 指定でコメントを取得 |
| `create_comment` | Note にコメントを作成 |
| `update_comment` | コメントを更新 |
| `delete_comment` | コメントを削除 |

## CLI での起動

```bash
uv run python -m example.mcp
```

サーバーは stdin/stdout（stdio トランスポート）でリッスンします — MCP の標準形式。

## カスタムトランスポート

```python
from example.mcp import create_mcp_server

server = create_mcp_server()
server.run(transport="sse")          # Server-Sent Events
server.run(transport="streamable-http")  # HTTP ストリーミング
```
