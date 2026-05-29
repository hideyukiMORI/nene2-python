# 操作指南：RFC 9457 Problem Details

## 基本用法

`problem_details_response()` 是一个工厂函数，返回符合 RFC 9457 规范的 JSON 错误响应。

```python
from nene2.http import problem_details_response

return problem_details_response(
    problem_type="not-found",
    title="Not Found",
    status=404,
    detail="Article ID 42 does not exist",
    extra={"article_id": 42},
)
```

响应示例：

```json
{
  "type": "https://nene2.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Article ID 42 does not exist",
  "article_id": 42
}
```

Content-Type 自动设置为 `application/problem+json`。

---

## 设置项目级 base_url

若要将默认 `base_url`（`https://nene2.dev/problems/`）改为项目专用 URL，在应用启动时调用一次 `configure_problem_details()`。

```python
# 在应用工厂中，例如 app.py
from nene2.http import configure_problem_details

configure_problem_details(base_url="https://api.myapp.com/problems/")
```

之后无需每次传入 `base_url`：

```python
# handler 中可省略 base_url
return problem_details_response("not-found", "Not Found", 404)
# → type: "https://api.myapp.com/problems/not-found"
```

如需对某次调用使用不同的 `base_url`，显式传入即可覆盖。

---

## 使用类型安全的常量管理 problem_type

`problem_type` 以字符串字面量传入，拼写错误不会被 mypy 检测到。在项目中使用 `StrEnum` 进行类型安全管理。

```python
from enum import StrEnum

class ProblemType(StrEnum):
    NOT_FOUND = "not-found"
    UNAUTHORIZED = "unauthorized"
    VALIDATION_FAILED = "validation-failed"
    ARTICLE_NOT_FOUND = "article-not-found"
```

用法：

```python
from nene2.http import problem_details_response
from .problems import ProblemType

return problem_details_response(ProblemType.NOT_FOUND, "Not Found", 404)
```

`StrEnum` 是 `str` 的子类，与 `problem_details_response()` 的 `str` 参数兼容。

---

## 与 ErrorHandlerMiddleware 集成

`ErrorHandlerMiddleware` 自动将 `ValidationException` 转换为 `problem_details_response()`，无需手动处理。

```python
# 自动变为 422 + application/problem+json
raise ValidationException.single("title", "Title is required", "required")
```

响应：

```json
{
  "type": "https://nene2.dev/problems/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "detail": "The request contains invalid values.",
  "errors": [{"field": "title", "message": "Title is required", "code": "required"}]
}
```
