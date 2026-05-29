# 操作指南：处理验证错误

如何使用 `nene2.validation` 中的 `ValidationException` 和 `ValidationError` 向客户端返回领域验证错误。

---

## 1. 将 ValidationCode 定义为 StrEnum

框架不定义标准错误码，请在项目中用 `StrEnum` 定义。

```python
from enum import StrEnum

class ValidationCode(StrEnum):
    REQUIRED = "required"
    INVALID_FORMAT = "invalid_format"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    ALREADY_EXISTS = "already_exists"
    OUT_OF_RANGE = "out_of_range"
```

使用 `StrEnum` 的好处：
- 可直接传入 `ValidationError` 构造函数（类型安全）
- 在 JSON 中序列化为字符串值
- 支持 IDE 补全和静态分析

---

## 2. 验证多个字段

将错误累积到列表中，然后一次性抛出 `ValidationException`。

```python
from nene2.validation import ValidationError, ValidationException

def validate_registration(username: str, email: str, age: int) -> None:
    errors: list[ValidationError] = []

    if len(username) < 3:
        errors.append(ValidationError("username", "At least 3 characters required", ValidationCode.TOO_SHORT))
    if "@" not in email:
        errors.append(ValidationError("email", "Enter a valid email address", ValidationCode.INVALID_FORMAT))
    if age < 0 or age > 150:
        errors.append(ValidationError("age", "Age must be between 0 and 150", ValidationCode.OUT_OF_RANGE))

    if errors:
        raise ValidationException(errors)
```

响应示例（422）：

```json
{
  "type": "https://example.com/problems/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "errors": [
    {"field": "username", "message": "At least 3 characters required", "code": "too_short"},
    {"field": "email",    "message": "Enter a valid email address", "code": "invalid_format"}
  ]
}
```

---

## 3. 验证单个字段

`ValidationException.single()` 只需一行即可抛出。

```python
from nene2.validation import ValidationException

raise ValidationException.single("email", "Email is required", ValidationCode.REQUIRED)
```

---

## 4. 嵌套字段的路径

以点分隔字符串传入嵌套字段路径（无规范化辅助函数）。

```python
ValidationError("address.city", "Required", ValidationCode.REQUIRED)
ValidationError("items.0.quantity", "Enter 1 or more", ValidationCode.OUT_OF_RANGE)
```

---

## 5. `@model_validator` 错误的字段名为 "request"

在 Pydantic 的 `@model_validator(mode="after")` 中 `raise ValueError(...)` 时，`loc` 为空元组。nene2 的 `ValidationException` 转换将其映射为 `field: "request"`。

```python
class RegisterBody(BaseModel):
    password: str
    password_confirm: str

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self
```

响应示例（422）：

```json
{
  "errors": [
    {
      "field": "request",
      "message": "Value error, Passwords do not match",
      "code": "value_error"
    }
  ]
}
```

在前端中，将 `field: "request"` 视为整个表单的错误，并在错误消息文本中包含相关字段名。

---

## 6. 与 ErrorHandlerMiddleware 集成

向应用添加 `nene2.middleware.ErrorHandlerMiddleware` 后，`ValidationException` 会自动转换为 422 Problem Details 响应。

```python
from nene2.middleware import ErrorHandlerMiddleware

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)
```

---

## 7. 对外部输入解码失败返回 400

Pydantic 的 `Query()` / `Body()` 在类型转换失败时会返回 422。但对于"以字符串接收并自行解码"的内容 — 如游标（Base64）、Token 等 — 若不捕获解码异常，`ErrorHandlerMiddleware` 会将其作为 500 返回。

```python
from fastapi.responses import JSONResponse

@app.get("/posts")
def list_posts(after: str | None = Query(None)) -> JSONResponse:
    if after is not None:
        try:
            cursor_id = _decode_cursor(after)  # 例如 base64.urlsafe_b64decode
        except Exception:
            return JSONResponse({"detail": "Invalid cursor"}, status_code=400)
        # 继续使用 cursor_id
```

将 `binascii.Error` 等解码失败通过 `ValueError` / `Exception` 一起捕获，返回 `400 Bad Request` — 这是用户输入错误，而非服务器错误。
