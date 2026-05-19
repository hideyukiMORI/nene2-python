# MCP セットアップガイド — Claude Desktop 連携

## 概要

`example/mcp.py` は Note と Tag の全 UseCase (10個) を MCP ツールとして公開する。
Claude Desktop や `claude` CLI から直接 CRUD 操作が可能になる。

## 前提

- `uv sync` 完了済み
- Python 3.12+ 環境

## Claude Desktop への設定

`claude_desktop_config.json` に以下を追加する:

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
        "example"
      ],
      "env": {
        "DB_ADAPTER": "sqlite",
        "DB_NAME": "/path/to/nene2-python/data/nene2.db"
      }
    }
  }
}
```

`/path/to/nene2-python` をリポジトリの絶対パスに変更すること。

## claude CLI での起動確認

```bash
# ファイル永続化 SQLite で起動
DB_ADAPTER=sqlite DB_NAME=./data/nene2.db uv run python -m example

# インメモリ SQLite（テスト用）
uv run python -m example
```

## 利用可能なツール

| ツール | 説明 |
|---|---|
| `list_notes(limit, offset)` | Note 一覧取得 |
| `get_note(note_id)` | Note 1件取得 |
| `create_note(title, body)` | Note 作成 |
| `update_note(note_id, title, body)` | Note 更新 |
| `delete_note(note_id)` | Note 削除 |
| `list_tags(limit, offset)` | Tag 一覧取得 |
| `get_tag(tag_id)` | Tag 1件取得 |
| `create_tag(name)` | Tag 作成 |
| `update_tag(tag_id, name)` | Tag 更新 |
| `delete_tag(tag_id)` | Tag 削除 |

## データディレクトリの準備

```bash
mkdir -p data
```

SQLite ファイルは初回起動時に自動作成される。
