# Field Trial 4 — snippets: SQLite共有MCP・ApiKey認証・CORSのDX検証

## Date

2026-05-19

## Baseline

- nene2-python v0.1.0 (`uv add git+https://github.com/hideyukiMORI/nene2-python.git`)
- Python 3.14.5（uv managed）
- プロジェクト: **snippets** — コードスニペット管理 JSON API
- エンティティ: `Snippet`（title, language, code）— 5 エンドポイント（CRUD）
- **`SqlAlchemySnippetRepository`（SQLite ファイル）** — HTTP API と MCP が共有
- **`ApiKeyAuthMiddleware`** ← FT1〜FT3 との差分①
- **`CORSMiddleware`** ← FT1〜FT3 との差分②
- **MCP + SQLite 共有** ← FT3-F2 の修正実証

## Goal

1. FT3-F2（MCP と HTTP API の状態共有）を SQLite で実証する
2. `ApiKeyAuthMiddleware`（X-Api-Key ヘッダー）の設定体験を確認する
3. `CORSMiddleware` の設定体験を確認する（FT3-F1 修正後の JSON 配列形式）
4. 3 つを同時に組み合わせたときの摩擦を洗い出す

---

## Steps Taken

### 1. プロジェクト初期化・インストール

問題なし。FT1〜FT3 で確立されたパターン通り。

### 2. `.env` 設定

FT3-F1 修正後のドキュメントを参照。JSON 配列形式を迷わず使えた：

```dotenv
API_KEYS=["ft4-api-key-1"]
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

→ FT3-F1 修正が効いていることを確認 ✓

### 3. ApiKeyAuthMiddleware

X-Api-Key なし → 401（`"A valid X-Api-Key header is required."`）✓
X-Api-Key あり → 200 ✓

### 4. CORSMiddleware + ApiKeyAuthMiddleware の同時利用

最初の `add_middleware` 登録順：

```python
# 誤った順序（最初に書いたコード）
app.add_middleware(CORSMiddleware, ...)   # 先に登録 = 内側
app.add_middleware(ApiKeyAuthMiddleware, ...)  # 後に登録 = 外側 ← preflight を遮断
```

OPTIONS preflight → 401 になり CORS が機能しなかった（**F-1**）。

修正後（CORS を後に登録して外側にする）：

```python
app.add_middleware(ApiKeyAuthMiddleware, ...)  # 先に登録 = 内側
app.add_middleware(CORSMiddleware, ...)         # 後に登録 = 外側 ← preflight が通る
```

→ OPTIONS preflight → 200 + `access-control-allow-origin` 付き ✓

### 5. MCP + SQLite 状態共有（FT3-F2 実証）

HTTP API と MCP サーバーに同一の `DB_NAME=/tmp/ft4-snippets.db` を設定：

- HTTP API でスニペット作成 → MCP `list_snippets` で確認 → **見える** ✓
- MCP `create_snippet` で作成 → HTTP API `GET /snippets` で確認 → **見える** ✓

FT3-F2 の修正（ドキュメントでの説明）が正しかったことを実動で証明。

---

## Friction Points

### F-1 CORS + Auth 同時利用時のミドルウェア登録順が非自明

**severity**: 高
**type**: ドキュメント不足

`CORSMiddleware` と `ApiKeyAuthMiddleware`（または `BearerTokenMiddleware`）を
同時に使う場合、**CORS を後に登録して外側に置かないと OPTIONS preflight が 401 になる**。

Starlette の逆順ルール（後に登録したものが外側）は既にドキュメントにあるが、
「CORS は Auth より外側にしなければならない」という組み合わせ固有のルールがない。

```python
# 正しい登録順（コメントは実行時の順序）
app.add_middleware(ErrorHandlerMiddleware, ...)    # ① 最初に実行（最内側）
app.add_middleware(SecurityHeadersMiddleware)      # ②
app.add_middleware(RequestIdMiddleware)            # ③
app.add_middleware(RequestLoggingMiddleware)       # ④
app.add_middleware(RequestSizeLimitMiddleware, ...) # ⑤
app.add_middleware(ThrottleMiddleware, ...)         # ⑥（任意）
app.add_middleware(ApiKeyAuthMiddleware, ...)       # ⑦ Auth
app.add_middleware(CORSMiddleware, ...)             # ⑧ 最後に実行（最外側）← CORS は必ず最後
```

**Follow-up**: ミドルウェアの組み合わせパターンを `docs/reference/framework-modules.md` と
`docs/how-to/new-project.md` に追記する。

---

## Summary

| ID  | 摩擦                                            | 深刻度 | 種別             | Follow-up Issue |
|-----|-------------------------------------------------|--------|------------------|-----------------|
| F-1 | CORS + Auth 同時利用時の登録順が非自明（preflight 401）| 高     | ドキュメント不足 | #90             |

FT2/FT3 で修正した以下の項目はすべてスムーズに動作：
- SQLite 永続化リポジトリパターン（#73）
- `write()` 返り値（#74）
- `db_url` 生成（#75）
- `list[str]` の JSON 配列形式（#81）
- MCP + SQLite 共有（#82）— 実動で証明

次回 FT5 は WebSocket または `SqlAlchemyTransactionManager.transactional()` の検証を推奨。
または F-1 修正後に PyPI 公開フローに移行するタイミング。
