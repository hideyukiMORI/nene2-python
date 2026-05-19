# Field Trial 9 — recipe: HttpxMcpClient + streamable-http トランスポート DX 検証

## Date

2026-05-20

## Baseline

- nene2-python v1.1.0（PyPI 経由）→ LocalMcpServer 修正後は local editable
- Python 3.14（uv managed）
- プロジェクト: **recipe** — レシピ管理 API
- エンティティ: `Recipe(id, title, description, servings)`
- HTTP API: ポート 8100（FastAPI + InMemory）
- MCP サーバー: ポート 8101（`streamable-http` トランスポート）
- MCP ツール: `HttpxMcpClient` で HTTP API を呼び出してデータ共有

## Goal

FT1〜FT8 で未探索のパターンを検証：

1. **`LocalMcpServer.run(transport="streamable-http")`** — HTTP モード MCP の起動
2. **`HttpxMcpClient`** — MCP ツールハンドラーから HTTP API を呼び出してデータ共有
3. FT3-F2（MCP と HTTP API のメモリ非共有問題）の正しい解決パターンを実証

---

## Steps Taken

### 1. HTTP API + MCP サーバーの二段構成

```
HTTP API（app.py, port 8100）
    ↑ HTTP calls
MCP Server（mcp_server.py, port 8101）
    ↓ streamable-http
Claude / MCP Client
```

MCP ツールが `HttpxMcpClient` で HTTP API を叩くため、どちらの経路から書いても同じデータが見える。

### 2. HttpxMcpClient でのツール実装

```python
from nene2.mcp import LocalMcpServer
from nene2.mcp.http_client import HttpxMcpClient

client = HttpxMcpClient()
server = LocalMcpServer("recipe-api", instructions="...", port=8101)

@server.tool("List all recipes. Returns paginated results.")
def list_recipes(limit: int = 20, offset: int = 0) -> str:
    response = client.get(API_BASE, f"/recipes?limit={limit}&offset={offset}")
    return response.body

@server.tool("Create a new recipe.")
def create_recipe(title: str, description: str, servings: int) -> str:
    response = client.post(API_BASE, "/recipes",
        {"title": title, "description": description, "servings": servings})
    return response.body
```

### 3. 動作確認

```bash
# HTTP API で作成 → MCP ツールから見える
curl -X POST http://localhost:8100/recipes -d '{"title":"Ramen",...}' → {"id":1,...}
MCP: list_recipes() → {"items":[{"id":1,"title":"Ramen",...}],...}

# MCP ツールで作成 → HTTP API から見える
MCP: create_recipe("Sushi",...) → {"id":2,...}
curl GET http://localhost:8100/recipes → [Ramen, Sushi]
```

**FT3-F2 の解決確認**: HTTP API と MCP が `HttpxMcpClient` 経由で完全にデータを共有。

### 4. streamable-http プロトコルのフロー

```
POST /mcp (initialize) → Session-ID: {uuid} を取得
POST /mcp + Mcp-Session-Id: {uuid} (tools/list, tools/call)
```

stdio と異なり、MCP セッション管理が必要。HTTP クライアントライブラリや Claude Desktop が処理するため、手動操作は検証時のみ。

---

## Friction Points

### FT9-1: `LocalMcpServer` にポート指定がない

- **摩擦**: `LocalMcpServer.run(transport="streamable-http")` のデフォルトポートが 8000 で変更不可
- `FastMCP.__init__` は `host`/`port` を受け取るが、`LocalMcpServer.__init__` が渡していなかった
- HTTP API（8100）と MCP（8101）を同一マシンで動かす際にポート衝突が起きる
- **深刻度**: HIGH（2サービス構成で必ずぶつかる）
- **解決策**: `LocalMcpServer.__init__(name, instructions, *, host, port)` に追加済み（PR #174）

### FT9-2: HTTP エラー（404 等）が `isError: false` で返る

- **摩擦**: MCP ツールが `return response.body` で 404 レスポンスをそのまま返すと、
  MCP プロトコルの `isError` フラグが `false` になる
- AI クライアントがエラーを成功として解釈する可能性がある
- **深刻度**: MEDIUM（AI がエラーを無視して誤った操作を続けるリスク）
- **解決策**: `McpHttpResponse.raise_for_error()` を追加 → FastMCP が例外を `isError: true` に変換（PR #174）

  ```python
  def get_recipe(recipe_id: int) -> str:
      response = client.get(API_BASE, f"/recipes/{recipe_id}")
      response.raise_for_error()   # ← 追加: 4xx/5xx を例外に変換
      return response.body
  ```

### FT9-3: DELETE が 204 No Content を返し `response.body` が空

- **摩擦**: DELETE エンドポイントは 204 を返すため `response.body` が空文字列 `""`
- MCP ツールの戻り値が `""` になり、AI が「削除完了」を確認できない
- **解決策**: 明示的に確認メッセージを組み立てる（フレームワークは解決不要、パターンとして文書化）

  ```python
  def delete_recipe(recipe_id: int) -> str:
      response = client.delete(API_BASE, f"/recipes/{recipe_id}")
      response.raise_for_error()
      if response.status_code == 204:
          return json.dumps({"deleted": True, "recipe_id": recipe_id})
      return response.body
  ```

### FT9-4: streamable-http はセッション管理が必要（stdio より複雑）

- **摩擦**: stdio はプロセス間通信で自動管理されるが、HTTP モードは `initialize` → Session ID → ツール呼び出し の2ステップ
- Claude Desktop や MCP SDK クライアントが透過的に処理するため、**実際の利用では問題にならない**
- ただしデバッグ時（curl で直接叩く）には手順が煩雑
- **深刻度**: LOW（ツール側の問題ではなく、デバッグ時の利便性の問題）

---

## Summary

| ID     | 摩擦                                            | 深刻度 | 解決策                                        |
|--------|-------------------------------------------------|--------|-----------------------------------------------|
| FT9-1  | LocalMcpServer にポート指定がない               | HIGH   | `host`/`port` 引数追加済み（PR #174）         |
| FT9-2  | HTTP エラーが isError: false で返る             | MEDIUM | `raise_for_error()` 追加済み（PR #174）       |
| FT9-3  | DELETE 204 で body が空 → AI が確認できない     | LOW    | パターンとして文書化（json.dumps で補完）      |
| FT9-4  | streamable-http のセッション管理が手動で煩雑    | LOW    | クライアント SDK が透過処理するので運用上は問題なし |

**`HttpxMcpClient` + `streamable-http` の組み合わせは FT3-F2 の正しい解決策として機能した。**
HTTP API を中継することで、MCP と HTTP クライアントが完全にデータを共有できる。

FT10 候補:
- **MySQL/PostgreSQL アダプター**: SQLite 以外の DB を初めて FT で使用
- **`BearerTokenMiddleware` + `HttpxMcpClient`**: 認証付き API に対して MCP から呼び出す
- **`LocalMcpServer` の SSE トランスポート**: `streamable-http` との差異を確認
