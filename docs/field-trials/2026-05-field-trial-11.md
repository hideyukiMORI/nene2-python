# Field Trial 11 — journal: BearerTokenMiddleware + HttpxMcpClient DX 検証

## Date

2026-05-20

## Baseline

- nene2-python v1.3.0（PyPI 経由）
- Python 3.14（uv managed）
- プロジェクト: **journal** — 日記管理 API
- エンティティ: `Entry(id, title, body, created_at)`
- HTTP API: ポート 8120（BearerTokenMiddleware 付き、InMemory）
- MCP サーバー: ポート 8121（streamable-http）

## Goal

FT9 で `HttpxMcpClient` の基本（認証なし）は確認済み。
今回は `BearerTokenMiddleware` で保護した HTTP API に対して MCP ツールが認証付きリクエストを送るパターンを検証する。

---

## Steps Taken

### 1. BearerTokenMiddleware で HTTP API を保護

```python
tokens = [t.strip() for t in os.getenv("BEARER_TOKENS", "").split(",") if t.strip()]
if tokens:
    app.add_middleware(BearerTokenMiddleware, verifier=LocalTokenVerifier(tokens))
```

環境変数 `BEARER_TOKENS=secret-token-1,secret-token-2` でカンマ区切りの複数トークンを設定。

### 2. MCP サーバーから認証付きで呼び出す

```python
token = os.getenv("MCP_BEARER_TOKEN", "")
client = HttpxMcpClient(token if token else None)

@server.tool("List all journal entries.")
def list_entries(limit: int = 20, offset: int = 0) -> str:
    response = client.get(API_BASE, f"/entries?limit={limit}&offset={offset}")
    response.raise_for_error()
    return response.body
```

`MCP_BEARER_TOKEN=secret-token-1` を MCP サーバーの環境変数に設定。
`HttpxMcpClient(token)` が `Authorization: Bearer <token>` ヘッダーを自動付与。

### 3. 動作確認

```
# MCP → 認証付き API → 成功
create_entry("First Entry", "Hello from MCP!") → {"id":1,...}
list_entries() → {"items":[{"id":1,...}],...}

# 誤トークン → 401 → raise_for_error() → isError: true
HTTP 401: {"type":"...unauthorized","detail":"The provided token is invalid or expired."}
```

---

## Friction Points

### FT11-1: `BearerTokenMiddleware` が `/docs`・`/openapi.json` まで保護する

- **摩擦**: ミドルウェアがすべてのパスに適用されるため、
  FastAPI の Swagger UI (`/docs`) や OpenAPI スキーマ (`/openapi.json`) にアクセスできなくなる
  ```
  GET /docs → 401 Unauthorized
  GET /openapi.json → 401 Unauthorized
  ```
- ロードバランサーの `/health` チェックも同様にブロックされる
- **現状の回避策**: 開発時は `BEARER_TOKENS=` を空にして認証を無効化
- **深刻度**: HIGH（開発・運用の両方で問題になる。特にヘルスチェックのブロックは本番障害につながる）
- **解決策**: `BearerTokenMiddleware(app, verifier=..., exclude_paths=["/docs", "/openapi.json", "/health"])` で除外パスを指定できるようにする

### FT11-2: `MCP_BEARER_TOKEN` 未設定時に分かりにくい 401 エラー

- **摩擦**: MCP サーバー起動時に `MCP_BEARER_TOKEN` が未設定の場合、
  `HttpxMcpClient(None)` になって認証ヘッダーなしで API を呼ぶ
- MCP ツール呼び出しが `HTTP 401` で失敗するが、エラーメッセージからトークン未設定が原因と気づきにくい
  ```
  McpHttpError: HTTP 401: {"detail":"A valid Bearer token is required."}
  ```
- **深刻度**: LOW（エラーメッセージを読めば原因はわかる）
- **解決策**: `mcp_server.py` でトークン未設定時に起動時警告を出す（フレームワーク対応不要、パターン文書化）

### FT11-3: `LocalTokenVerifier` がカンマ区切り文字列の分割を要求する

- **摩擦**: 複数トークンを環境変数で渡す標準パターンがなく、アプリ側でカンマ分割処理を書く必要がある
  ```python
  tokens = [t.strip() for t in os.getenv("BEARER_TOKENS", "").split(",") if t.strip()]
  ```
- FT3 でも同様のコードを書いていた（重複パターン）
- **深刻度**: LOW（数行のコードだが、毎回書く必要がある）
- **解決策**: `LocalTokenVerifier.from_env("BEARER_TOKENS")` クラスメソッドを追加

---

## Summary

| ID     | 摩擦                                                     | 深刻度 | 解決策                                          |
|--------|----------------------------------------------------------|--------|-------------------------------------------------|
| FT11-1 | `BearerTokenMiddleware` が `/docs`・`/health` もブロック | HIGH   | `exclude_paths` 引数を追加                      |
| FT11-2 | `MCP_BEARER_TOKEN` 未設定時の 401 が原因不明に見える     | LOW    | 起動時警告パターンを文書化                      |
| FT11-3 | `LocalTokenVerifier` の複数トークン設定にボイラープレート | LOW    | `LocalTokenVerifier.from_env()` クラスメソッド |

**`HttpxMcpClient(bearer_token)` + `raise_for_error()` の組み合わせは期待通りに動作した。**
認証エラー（401）は `McpHttpError` として raise され、MCP の `isError: true` に正しく変換される。

FT12 候補:
- **FT11-1 の修正**: `BearerTokenMiddleware` に `exclude_paths` を追加
- **PostgreSQL アダプター**: `RETURNING` 句が使えるかを検証
- **SSE トランスポート**: `streamable-http` との差異を確認
