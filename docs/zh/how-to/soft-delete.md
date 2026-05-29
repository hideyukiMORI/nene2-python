# 操作指南：软删除（逻辑删除）

使用 `deleted_at: datetime | None` 字段实现逻辑删除的模式。

---

## 领域实体

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

`is_deleted` 属性将业务逻辑封装在领域内，调用方无需判断 `deleted_at is not None`。

---

## 更新 frozen dataclass：dataclasses.replace()

```python
from dataclasses import replace

article = replace(article, deleted_at=datetime.now(UTC))
```

`frozen=True` 的 dataclass 不能直接修改字段，但 `replace()` 可以创建新实例。

---

## DELETE endpoint（幂等）

```python
@app.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int) -> None:
    article = _store.get(article_id)
    if article is None or article.is_deleted:
        return  # 幂等：已删除或不存在也返回 204
    _store[article_id] = replace(article, deleted_at=datetime.now(UTC))
```

根据 RFC 9110，DELETE 是幂等的。对不存在或已删除的资源执行 DELETE 也返回 204。

---

## 在列表和查询中排除已删除项

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
    return ArticleResponse.from_domain(article)  # 成功时返回模型实例（默认模式）
```

---

## 从响应中排除 deleted_at

只需不在 `ArticleResponse` 中定义 `deleted_at` 字段即可，Pydantic 不会序列化未定义的字段。

```python
class ArticleResponse(BaseModel):
    article_id: int
    title: str
    # deleted_at 不包含 → 逻辑删除的实现细节不泄露到公开 API 中
```

推荐设计：仅在管理员 endpoint 上返回 `deleted_at`。

---

## 参阅

- FT110: `docs/field-trials/2026-05-field-trial-110.md`
