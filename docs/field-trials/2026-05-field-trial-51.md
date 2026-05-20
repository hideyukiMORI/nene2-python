# Field Trial 51: SimpleDomainHandler 実運用検証

**Date**: 2026-05-20
**Theme**: `SimpleDomainHandler` + `detail_factory` / `extra_factory` の実運用パターン検証
**Version under test**: v1.8.10
**FT App**: `/home/xi/docker/nene2-python-FT/ft51-domain-handler/`

---

## 概要

複数のドメイン例外を `SimpleDomainHandler` で Problem Details に変換するパターンを
記事 API で実運用した。404 / 403 / 409 の 3 種類のエラーを検証。

---

## 実装内容

### ドメイン例外クラス

```python
class ArticleNotFoundError(Exception):
    def __init__(self, article_id: int) -> None:
        self.article_id = article_id

class ArticleAccessDeniedError(Exception):
    def __init__(self, article_id: int, user_id: str) -> None:
        self.article_id = article_id
        self.user_id = user_id

class ArticleTitleConflictError(Exception):
    def __init__(self, title: str) -> None:
        self.title = title
```

### SimpleDomainHandler による登録

```python
handlers = [
    SimpleDomainHandler(
        ArticleNotFoundError,
        "article-not-found",
        "Article Not Found",
        404,
        detail_factory=lambda exc: str(exc),
        extra_factory=lambda exc: {"article_id": exc.article_id},
    ),
    SimpleDomainHandler(
        ArticleAccessDeniedError,
        "article-access-denied",
        "Access Denied",
        403,
        detail_factory=lambda exc: str(exc),
        extra_factory=lambda exc: {"article_id": exc.article_id, "user_id": exc.user_id},
    ),
    SimpleDomainHandler(
        ArticleTitleConflictError,
        "article-title-conflict",
        "Article Title Conflict",
        409,
        detail_factory=lambda exc: str(exc),
        extra_factory=lambda exc: {"article_title": exc.title},  # ← "title" ではなく "article_title"
    ),
]
app.add_middleware(ErrorHandlerMiddleware, domain_handlers=handlers)
```

---

## テスト結果

6 tests, all passed (after fixing FP51-1).

---

## 摩擦ポイント

### FP51-1: `extra_factory` に `title` キーを返すと Problem Details の `title` が上書きされる

**状況**: `ArticleTitleConflictError` の `extra_factory` で `{"title": exc.title}` を返したところ、
Problem Details レスポンスの `title` フィールド（`"Article Title Conflict"`）が `exc.title`（`"Dup"`）に
上書きされた。

```json
{
  "type": "...",
  "title": "Dup",      // ← "Article Title Conflict" のはずが上書きされた
  "status": 409,
  "detail": "Article with title 'Dup' already exists"
}
```

**原因**: `problem_details_response()` が `body.update(extra)` で `extra` を後から適用するため、
RFC 9457 の予約済みフィールド (`type`, `title`, `status`, `detail`) を含む `extra` が
意図せずフィールドを上書きする。

**修正**: `problem_details_response()` が `extra` に予約済みフィールドが含まれている場合に
`ValueError` を raise するよう修正 (#282)。

```python
# 修正後のコード
_RESERVED_FIELDS = frozenset({"type", "title", "status", "detail"})
if extra:
    overlap = _RESERVED_FIELDS & extra.keys()
    if overlap:
        raise ValueError(f"extra contains reserved Problem Details fields: {sorted(overlap)}")
    body.update(extra)
```

**ワークアラウンド（修正前）**: `extra` に予約済みキーと衝突しない名前を使う（例: `"article_title"`）。

---

## フレームワーク変更

### `nene2.http.problem_details_response()` — extra reserved fields 保護 (#282)

`extra` に RFC 9457 予約済みフィールド (`type`, `title`, `status`, `detail`) が含まれる場合に
`ValueError` を raise するようになった。

---

## 結論

`SimpleDomainHandler` + `detail_factory` / `extra_factory` の組み合わせは実運用で使いやすい。
ただし `extra_factory` の返り値に RFC 9457 予約済みフィールドと同名のキーを入れると
サイレントに上書きされる危険があった。`ValueError` による早期検知で問題を防止できる。
