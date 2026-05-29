# How-to: RFC 9457 Problem Details

## 基本的な使い方

`problem_details_response()` は RFC 9457 準拠の JSON エラー応答を返すファクトリ関数です。

```python
from nene2.http import problem_details_response

return problem_details_response(
    problem_type="not-found",
    title="Not Found",
    status=404,
    detail="記事 ID 42 は存在しません",
    extra={"article_id": 42},
)
```

レスポンス例:

```json
{
  "type": "https://nene2.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "記事 ID 42 は存在しません",
  "article_id": 42
}
```

Content-Type は自動で `application/problem+json` になります。

---

## プロジェクト全体の base_url を設定する

デフォルトの `base_url` (`https://nene2.dev/problems/`) をプロジェクト固有の URL に変更するには、
アプリ起動時に一度だけ `configure_problem_details()` を呼び出します。

```python
# app.py などのアプリケーションファクトリ
from nene2.http import configure_problem_details

configure_problem_details(base_url="https://api.myapp.com/problems/")
```

以降は `base_url` を毎回渡す必要がなくなります:

```python
# ハンドラーで base_url を省略できる
return problem_details_response("not-found", "Not Found", 404)
# → type: "https://api.myapp.com/problems/not-found"
```

特定の呼び出しで一時的に別の `base_url` を使いたい場合は、引数で明示すれば上書きできます。

---

## problem_type に型安全な定数を使う

`problem_type` は文字列リテラルで渡すため、タイポがあっても mypy では検出されません。
プロジェクト内で `StrEnum` を使うと型安全に管理できます。

```python
from enum import StrEnum

class ProblemType(StrEnum):
    NOT_FOUND = "not-found"
    UNAUTHORIZED = "unauthorized"
    VALIDATION_FAILED = "validation-failed"
    ARTICLE_NOT_FOUND = "article-not-found"
```

使用例:

```python
from nene2.http import problem_details_response
from .problems import ProblemType

return problem_details_response(ProblemType.NOT_FOUND, "Not Found", 404)
```

`StrEnum` は `str` のサブクラスなので、`problem_details_response()` の `str` 型引数と互換性があります。

---

## ErrorHandlerMiddleware との統合

`ErrorHandlerMiddleware` は `ValidationException` を自動的に `problem_details_response()` に変換するため、
手動で処理する必要はありません。

```python
# これは自動で 422 + application/problem+json になる
raise ValidationException.single("title", "タイトルは必須です", "required")
```

レスポンス:

```json
{
  "type": "https://nene2.dev/problems/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "detail": "The request contains invalid values.",
  "errors": [{"field": "title", "message": "タイトルは必須です", "code": "required"}]
}
```
