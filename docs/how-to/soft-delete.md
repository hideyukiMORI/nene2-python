# How-to: ソフトデリート（論理削除）

`deleted_at: datetime | None` フィールドで論理削除を実装するパターン。

---

## ドメイン Entity

```python
from dataclasses import dataclass
from datetime import UTC, datetime

@dataclass(frozen=True, slots=True)
class Article:
    article_id: int
    title: str
    deleted_at: datetime | None = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

`is_deleted` プロパティでビジネスロジックをドメインに閉じ込め、呼び出し側が `deleted_at is not None` を意識しないようにする。

---

## frozen dataclass の更新: dataclasses.replace()

```python
from dataclasses import replace

article = replace(article, deleted_at=datetime.now(UTC))
```

`frozen=True` な dataclass は直接フィールドを変更できないが、`replace()` で新しいインスタンスを作れる。

---

## DELETE エンドポイント（冪等）

```python
@app.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int) -> None:
    article = _store.get(article_id)
    if article is None or article.is_deleted:
        return  # 冪等: 既に削除済みや存在しない場合も 204
    _store[article_id] = replace(article, deleted_at=datetime.now(UTC))
```

RFC 9110 に従い、DELETE は冪等にする。存在しないリソースや削除済みリソースへの DELETE も 204 を返す。

---

## 一覧・取得での除外

```python
def _active_articles() -> list[Article]:
    return [a for a in _store.values() if not a.is_deleted]

@app.get("/articles", response_model=list[ArticleResponse])
def list_articles() -> list[ArticleResponse]:
    return [ArticleResponse.from_domain(a) for a in _active_articles()]

@app.get("/articles/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int) -> ArticleResponse | JSONResponse:
    article = _store.get(article_id)
    if article is None or article.is_deleted:
        return problem_details_response("not-found", "Not Found", 404, "Article not found.")
    return ArticleResponse.from_domain(article)  # 成功時はモデルを返す（既定パターン）
```

---

## deleted_at をレスポンスから除外する

`ArticleResponse` に `deleted_at` フィールドを定義しないだけでよい。
Pydantic は定義されていないフィールドをシリアライズしない。

```python
class ArticleResponse(BaseModel):
    article_id: int
    title: str
    # deleted_at は含めない → 公開 API に論理削除の実装詳細が漏れない
```

管理用エンドポイントのみ `deleted_at` を返す設計が推奨される。

---

## 参照

- FT110: `docs/field-trials/2026-05-field-trial-110.md`
