# Field Trial 92: APIRouter パターン

**日付**: 2026-05-20
**テーマ**: FastAPI の `APIRouter` を使ったドメイン分割パターン
**バージョン**: v1.8.30
**結果**: 摩擦あり（コード修正なし）

---

## 目的

FastAPI の `APIRouter` を使って複数ドメイン（記事・コメント）のルートを分割し、nene2 の `setup_middlewares()` との共存を検証する。

---

## 実施内容

`/home/xi/docker/nene2-python-FT/ft92-api-router/` に以下を実装:

- `routers/articles.py` — 記事 CRUD（prefix `/articles`、tags `["articles"]`）
- `routers/comments.py` — コメント CRUD（prefix `/articles/{article_id}/comments`、tags `["comments"]`）
- `app.py` — `setup_middlewares(app)` + `app.include_router()`
- 14 テスト（全 PASS）

---

## 摩擦点

### F92-1: OpenAPI トップレベルの `tags` は空

`FastAPI()` コンストラクタに `openapi_tags` を渡さない限り、`/openapi.json` の `tags` フィールド（トップレベル）は空リスト `[]` になる。

```python
# ❌ トップレベル tags は空
openapi = client.get("/openapi.json").json()
tags = [t["name"] for t in openapi.get("tags", [])]  # 常に []
assert "articles" in tags  # 失敗

# ✅ パスレベルの操作 tags を確認する
get_tags = openapi["paths"]["/articles"]["get"].get("tags", [])
assert "articles" in get_tags  # 成功
```

`openapi_tags` パラメーターはタグの説明を追加するためのもので、タグ自体はルーター定義の `tags=["articles"]` がパス操作レベルに反映される。

**影響**: OpenAPI ドキュメントに tags の description や externalDocs を載せたい場合は明示的に `openapi_tags` を渡す必要がある。

### F92-2: ルーターのグローバル変数はテスト間で共有される

`routers/articles.py` の `_articles: dict[int, Article]` はモジュールレベルの変数。pytest がモジュールをキャッシュするため、テスト間で共有される（FT86 の EventBus と同じ問題）。

`autouse` fixture でクリアすることで回避できるが、ルーターが内部状態を持つ設計自体が注意を要する。

```python
@pytest.fixture(autouse=True)
def reset_state() -> None:
    articles_module._articles.clear()
    articles_module._next_id = 1
    comments_module._comments.clear()
    comments_module._next_comment_id = 1
```

本番コードでは Repository に状態を持たせ、DI 経由で注入することでこの問題を回避できる。

### F92-3: ルーターの `prefix` は全ルートに適用される

`APIRouter(prefix="/articles")` を設定すると、そのルーターの全ルートに `/articles` が付く。`include_router(router, prefix="/v2/articles")` でオーバーライドすると、ルーター側の prefix と二重になる場合がある。

```python
# ルーター定義
router = APIRouter(prefix="/articles")  # prefix あり

# include_router でさらに prefix を付けると二重になる
app.include_router(router, prefix="/api")
# → /api/articles になる（意図通り）

app.include_router(router, prefix="/api/articles")
# → /api/articles/articles になる（意図しない二重 prefix）
```

prefix の責務をルーター側か include_router 側のどちらかに集約するルールを決めておく必要がある。

---

## 確認できた良好な動作

- `APIRouter` で分割したルートにも `X-Request-Id` ヘッダーが付く（RequestIdMiddleware との共存 OK）
- ネストされたリソース `/articles/{article_id}/comments` の path parameter が自動的にルートハンドラーに渡される
- `tags` がパス操作レベルで正しく反映される

---

## 結論

`APIRouter` は nene2 の `setup_middlewares()` と問題なく共存できる。
主な摩擦は OpenAPI の `tags` 挙動の把握と、モジュールレベルの状態管理の注意点。
いずれもコード修正は不要で、使用パターンの理解で対応できる。
