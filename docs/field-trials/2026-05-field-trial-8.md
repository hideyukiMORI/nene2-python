# Field Trial 8 — blog: 親子リソース (Nested REST) + datetime + SQLite 複数エンティティ

## Date

2026-05-20

## Baseline

- nene2-python v1.0.0（PyPI 経由 `uv add nene2-python`）
- Python 3.14（uv managed）
- プロジェクト: **blog** — ブログ API（投稿 + コメント）
- エンティティ:
  - `Post(id, title, body, created_at: datetime)`
  - `Comment(id, post_id, author, body, created_at: datetime)`
- SQLite ファイル永続化（`blog.db`）
- 8 エンドポイント: Post CRUD + コメント List/Create/Delete（Nested REST）

## Goal

FT1〜FT7 で未探索のパターンを一度に検証：

1. **親子リソース（Nested REST）**: `GET /posts/{id}/comments`、`POST /posts/{id}/comments`
2. **`datetime` フィールドを持つエンティティ**: `created_at` が SQLite → entity → JSON でどう流れるか
3. **SQLite 外部キー**: 2エンティティ間の参照整合性（`ON DELETE CASCADE`）
4. **`DatabaseHealthCheck`** の実際の動作確認

---

## Steps Taken

### 1. プロジェクト初期化

問題なし。`uv add nene2-python` 一行で完了。

### 2. エンティティに `datetime` フィールドを追加

```python
@dataclass(frozen=True, slots=True)
class Post:
    id: int
    title: str
    body: str
    created_at: datetime   # ← FT1〜FT7 で一度も使われなかったフィールド
```

FT1〜FT7 の全エンティティ（Note, Book, Task, Snippet, Wallet, City, Bookmark）は
`created_at` を持っていない。example の Note も schema に `created_at` カラムはあるが
エンティティ定義には含まれていない。**datetime フィールドの扱いは前例なし。**

### 3. SQLite スキーマ（外部キー + `CURRENT_TIMESTAMP`）

```python
# PRAGMA foreign_keys=ON で参照整合性を有効化
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    if isinstance(dbapi_conn, sqlite3.Connection):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

# comments テーブルに外部キー
"post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE"
```

`PRAGMA foreign_keys=ON` は example の schema.py を参照して発見。ドキュメントには記載なし。

### 4. SQLAlchemy Repository での datetime 変換

```python
def _to_post(row: dict[str, Any]) -> Post:
    return Post(
        id=row["id"],
        title=row["title"],
        body=row["body"],
        # SQLite は DATETIME を text 型で返す: "2026-05-20 12:34:56"
        created_at=datetime.fromisoformat(str(row["created_at"])).replace(tzinfo=timezone.utc),
    )
```

### 5. SELECT-after-INSERT パターン（DB生成タイムスタンプを取得）

```python
def save(self, title: str, body: str) -> Post:
    new_id = self._executor.write(
        "INSERT INTO posts (title, body) VALUES (:title, :body)",
        {"title": title, "body": body},
    )
    row = self._executor.fetch_one(
        "SELECT id, title, body, created_at FROM posts WHERE id = :id",
        {"id": new_id},
    )
    if row is None:
        raise RuntimeError(f"Row {new_id} not found after INSERT into posts")
    return _to_post(row)
```

INSERT → `write()` → `lastrowid` → `fetch_one()` の2往復が必要。

### 6. Nested REST ハンドラー

```python
@router.get("/posts/{post_id}/comments")
async def list_comments(post_id: int, request: Request) -> JSONResponse:
    pagination = PaginationQueryParser.parse(request)
    output = list_comments_use_case.execute(
        ListCommentsInput(post_id, pagination.limit, pagination.offset)
    )
    ...

@router.post("/posts/{post_id}/comments", status_code=201)
async def create_comment(post_id: int, body: CreateCommentBody) -> JSONResponse:
    ...
```

FastAPI がパスパラメータ `post_id` を UseCase に渡すため、ネストの実装自体は自然。

### 7. 動作確認

```
GET  /health
→ 200  {"status":"ok","checks":{"database":"ok"}}  ← DatabaseHealthCheck 正常

POST /posts  {"title":"Hello nene2","body":"First post"}
→ 201  {"id":1,"title":"Hello nene2","body":"First post","created_at":"2026-05-19T18:39:52+00:00"}

POST /posts/1/comments  {"author":"Alice","body":"Great!"}
→ 201  {"id":1,"post_id":1,"author":"Alice","body":"Great!","created_at":"2026-05-19T18:39:52+00:00"}

GET  /posts/1/comments?limit=10
→ 200  {"items":[...],"limit":10,"offset":0,"total":1}

POST /posts/999/comments  {...}
→ 404  {"type":"...not-found","detail":"Post 999 not found."}

DELETE /posts/1
→ 204  (cascade: comments も自動削除)

GET  /posts/1/comments  (削除後)
→ 404  Post 1 not found.
```

---

## Friction Points

### FT8-1: SQLite `CURRENT_TIMESTAMP` が naive datetime を返す — タイムゾーン情報が失われる

- **摩擦**: `CURRENT_TIMESTAMP` は UTC 時刻だが SQLite は `"2026-05-20 12:34:56"` という文字列で格納・返却する
- `datetime.fromisoformat("2026-05-20 12:34:56")` は **naive datetime**（tzinfo なし）を返す
- JSON にシリアライズすると `"2026-05-20T12:34:56"` — タイムゾーンが不明な時刻として API に漏れる
- **深刻度**: MEDIUM（API 利用者が UTC か JST か判断できない）
- **解決策**: `.replace(tzinfo=timezone.utc)` を明示的に追加
- **nene2 の対応**: `fetch_one` / `fetch_all` の戻り値に datetime フィールドのガイダンスがない

### FT8-2: `dict[str, object]` vs `dict[str, Any]` — 型注釈の落とし穴

- **摩擦**: `_to_post(row: dict[str, object])` と書くと `int(row["id"])` が mypy `call-overload` エラー
- `# type: ignore[arg-type]` を付けると「wrong error code」で `unused-ignore` が発生（二重エラー）
- **深刻度**: MEDIUM（mypy --strict を使う場合にブロッキング）
- **解決策**: `dict[str, Any]` を使う（`fetch_one()` の実際の戻り値型と一致）
- **根本原因**: nene2 の「row-to-entity 変換」サンプルに datetime フィールドがない

### FT8-3: SELECT-after-INSERT のボイラープレート

- **摩擦**: DB 生成の `CURRENT_TIMESTAMP` を取得するために INSERT → `lastrowid` → `fetch_one` の2往復が必要
- 毎 `save()` メソッドに同じパターンを書く（PostRepository と CommentRepository の両方）
- `fetch_one()` は `dict | None` を返すため、`if row is None: raise RuntimeError(...)` が必要
  - `assert row is not None` は ruff S101（本番コードで assert 禁止）で弾かれる
- **深刻度**: LOW（機能するが冗長）
- **検討**: `write_and_return(sql, params, select_sql)` のようなヘルパーをフレームワークに追加するか

### FT8-4: if/else で異なる実装を変数に代入すると mypy エラー

- **摩擦**:

  ```python
  if cfg.db_adapter == "sqlite":
      post_repo = SqlAlchemyPostRepository(executor)
  else:
      post_repo = InMemoryPostRepository()  # ← mypy: Incompatible types
  ```

- `mypy --strict` が `Incompatible types in assignment` を報告
- **解決策**: 事前に型注釈を宣言する

  ```python
  post_repo: PostRepositoryInterface
  ```

- **深刻度**: LOW（パターンを一度知れば1行で解決）
- example の `app.py` は `_build_repositories()` 関数で隠蔽しているため、このエラーが見えにくい

### FT8-5: Nested REST の `post_id` パスパラメータが DELETE で無視される — 設計の穴

- **摩擦**: `DELETE /posts/{post_id}/comments/{comment_id}` の `post_id` を DELETE ハンドラーが無視する
- `DELETE /posts/1/comments/2` が post 2 のコメント2（別ポストのコメント）を削除できてしまう
- REST セマンティクス的には `/posts/1/comments/2` は「post 1 に属するコメント2」を指すべき
- **深刻度**: MEDIUM（アクセス制御がある場合はセキュリティ問題になりうる）
- **解決策**: DELETE UseCase に `post_id` を含め、コメントの `post_id` と一致するか検証する
- **nene2 の対応**: ネストリソースの DELETE 設計についてガイダンスなし

---

## Summary

| ID     | 摩擦                                          | 深刻度 | 種別           | 解決策                              |
|--------|-----------------------------------------------|--------|----------------|-------------------------------------|
| FT8-1  | SQLite naive datetime — TZ情報が失われる      | MEDIUM | 設計/DB        | `.replace(tzinfo=timezone.utc)`    |
| FT8-2  | `dict[str, object]` vs `Any` — mypy エラー  | MEDIUM | 型安全         | `dict[str, Any]` を使う            |
| FT8-3  | SELECT-after-INSERT ボイラープレート          | LOW    | フレームワーク | `write_and_return()` ヘルパー検討  |
| FT8-4  | if/else 分岐での型注釈宣言が必要             | LOW    | 型安全         | `var: InterfaceType` を先に宣言    |
| FT8-5  | Nested DELETE で `post_id` が無視される       | MEDIUM | 設計           | UseCase に `post_id` を追加して検証 |

親子リソース（Nested REST）そのものの実装は **摩擦ゼロ** — FastAPI のパスパラメータが自然に機能した。
主な摩擦は `datetime` フィールドと `mypy --strict` 周辺に集中。

FT9 候補:
- **FT8-1/FT8-3 の改善**: nene2 フレームワークに `datetime` ユーティリティ / `write_and_return()` を追加して検証
- **MySQL/PostgreSQL**: SQLite 以外のアダプター（`RETURNING` 句が使えるので FT8-3 が解消されるか検証）
- **HttpxMcpClient**: HTTP モードの MCP クライアントを実地検証
