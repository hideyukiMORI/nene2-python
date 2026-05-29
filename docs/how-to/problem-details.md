# How-to: RFC 9457 Problem Details

## Basic usage

`problem_details_response()` is a factory that returns an RFC 9457-compliant JSON
error response.

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

Example response:

```json
{
  "type": "https://nene2.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Article ID 42 does not exist",
  "article_id": 42
}
```

The Content-Type is set to `application/problem+json` automatically.

---

## Set a project-wide base_url

To change the default `base_url` (`https://nene2.dev/problems/`) to a
project-specific URL, call `configure_problem_details()` once at app startup.

```python
# In the application factory, e.g. app.py
from nene2.http import configure_problem_details

configure_problem_details(base_url="https://api.myapp.com/problems/")
```

After that you no longer pass `base_url` every time:

```python
# base_url can be omitted in handlers
return problem_details_response("not-found", "Not Found", 404)
# → type: "https://api.myapp.com/problems/not-found"
```

To use a different `base_url` for a specific call, pass it explicitly to override.

---

## Use type-safe constants for problem_type

`problem_type` is passed as a string literal, so a typo won't be caught by mypy.
Manage them type-safely with a `StrEnum` in your project.

```python
from enum import StrEnum

class ProblemType(StrEnum):
    NOT_FOUND = "not-found"
    UNAUTHORIZED = "unauthorized"
    VALIDATION_FAILED = "validation-failed"
    ARTICLE_NOT_FOUND = "article-not-found"
```

Usage:

```python
from nene2.http import problem_details_response
from .problems import ProblemType

return problem_details_response(ProblemType.NOT_FOUND, "Not Found", 404)
```

`StrEnum` is a subclass of `str`, so it's compatible with the `str` parameter of
`problem_details_response()`.

---

## Integration with ErrorHandlerMiddleware

`ErrorHandlerMiddleware` automatically converts a `ValidationException` into a
`problem_details_response()`, so you don't need to handle it manually.

```python
# This becomes 422 + application/problem+json automatically
raise ValidationException.single("title", "Title is required", "required")
```

Response:

```json
{
  "type": "https://nene2.dev/problems/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "detail": "The request contains invalid values.",
  "errors": [{"field": "title", "message": "Title is required", "code": "required"}]
}
```
