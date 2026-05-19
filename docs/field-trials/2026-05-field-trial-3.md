# Field Trial 3 — tasklist: Bearer Token認証 + MCP サーバーの DX 検証

## Date

2026-05-19

## Baseline

- nene2-python v0.1.0 (`uv add git+https://github.com/hideyukiMORI/nene2-python.git`)
- Python 3.14.5（uv managed）
- プロジェクト: **tasklist** — タスク管理 JSON API
- エンティティ: `Task`（title, status, priority）— 5 エンドポイント（CRUD）
- **`BearerTokenMiddleware`** ← FT1/FT2 との差分①
- **`LocalMcpServer`（stdio）** ← FT1/FT2 との差分②

## Goal

1. `BearerTokenMiddleware` の設定・動作確認
2. `LocalMcpServer` を外部プロジェクトから設定し stdio 経由で動作確認
3. 両者の DX 摩擦を洗い出す

---

## Steps Taken

### 1. プロジェクト初期化・インストール

FT1/FT2 と同様、問題なし。

### 2. ドメイン層・HTTP ハンドラ実装

FT1〜FT2 で修正されたドキュメントを参照。ミドルウェアスタックは一発で正しく組めた。

### 3. Bearer Token 認証の設定

`.env` に `BEARER_TOKENS=dev-secret-token-1` と記述して起動 → **起動失敗**（F-1）。

JSON 形式 `BEARER_TOKENS=["dev-secret-token-1"]` に修正して解決。

動作確認：
- 認証なし → 401（`unauthorized` Problem Details）✓
- 間違ったトークン → 401（`The provided token is invalid or expired.`）✓
- 正しいトークン → 200 ✓

### 4. MCP サーバー実装

`LocalMcpServer` を使い `mcp_server.py` を実装。ツール登録はデコレータで直感的に書けた。

MCP プロトコルハンドシェイク（initialize → initialized → tools/list / tools/call）を
Python スクリプトで確認：

- `tools/list` → 5 ツール（list/get/create/update/delete）が正常に返る ✓
- `create_task` → `{"id":1,"title":"FT3 MCPテスト","status":"open","priority":"high"}` ✓
- `list_tasks` → 作成したタスクが返る ✓

### 5. Claude Desktop 接続

WSL2 環境で Claude Desktop が未インストールのため実機確認不可。
設定ファイルのサンプルをドキュメントに記載する形で代替。

---

## Friction Points

### F-1 `.env` で `list[str]` フィールドに JSON 形式が必要なのに記載なし

**severity**: 高
**type**: ドキュメント不足

`BEARER_TOKENS` / `API_KEYS` / `CORS_ORIGINS` など `list[str]` 型のフィールドは、
`.env` に plain text で書くと `JSONDecodeError` で起動失敗する。
JSON 形式（`["value1","value2"]`）が正解だが、`.env.example` やドキュメントに記載がない。

```dotenv
# NG — JSONDecodeError で起動失敗
BEARER_TOKENS=token-1,token-2

# OK
BEARER_TOKENS=["token-1","token-2"]
```

**Follow-up**: `docs/reference/configuration.md` と `.env.example` に list 型フィールドの
正しい書き方を明記する。

---

### F-2 MCP サーバーと HTTP API がメモリを共有しないことが不明確

**severity**: 中
**type**: ドキュメント / 設計説明不足

`mcp_server.py` が別プロセスとして動くため、HTTP API の `InMemoryTaskRepository` と
MCP サーバーの `InMemoryTaskRepository` は別インスタンスになる。
「MCP で作ったタスクが HTTP API から見えない」という混乱が起きやすい。

解決策は SQLite 等の永続化リポジトリを使うことだが、その指針がドキュメントにない。

**Follow-up**: MCP ハウツーに「InMemory は開発専用。MCP と HTTP で状態を共有するには
SQLite 等の永続化リポジトリを使う」旨を追記する。

---

### F-3 Claude Desktop の MCP 設定例（WSL2 パス）がない

**severity**: 中
**type**: ドキュメント不足

既存の `docs/howto/mcp-setup.md` に MCP 設定例はあるが、WSL2 からの uv コマンド呼び出し
パターン（`"command": "wsl"`, `"args": ["-e", "uv", ...]`）の記載がない。

Windows 上の Claude Desktop から WSL2 の uv プロジェクトを呼ぶには特殊なパス指定が必要。

**Follow-up**: `docs/howto/mcp-setup.md` に WSL2 向け設定例を追加する。

---

## Summary

| ID  | 摩擦                                          | 深刻度 | 種別             | Follow-up Issue |
|-----|-----------------------------------------------|--------|------------------|-----------------|
| F-1 | `list[str]` の `.env` 書き方が JSON 形式と知らない | 高     | ドキュメント不足 | TBD             |
| F-2 | MCP と HTTP API がメモリ共有しないことが不明確     | 中     | 設計説明不足     | TBD             |
| F-3 | Claude Desktop WSL2 設定例がない                  | 中     | ドキュメント不足 | TBD             |

FT2 で修正した SQLite 関連ドキュメント（#73〜#75）の効果は確認できた。

次回 FT4 は SQLite 永続化 + MCP 統合（MCP と HTTP で DB 共有）を推奨。
