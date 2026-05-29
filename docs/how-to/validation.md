# How-to: handling validation errors

How to return domain validation errors to the client using `ValidationException`
and `ValidationError` from `nene2.validation`.

---

## 1. Define ValidationCode as a StrEnum

The framework does not define standard error codes. Define them per project with a
`StrEnum`.

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

Using a `StrEnum`:
- can be passed directly to the `ValidationError` constructor (type-safe)
- serializes to its string value in JSON
- gets IDE completion and static analysis

---

## 2. Validating multiple fields

Accumulate errors in a list and raise a single `ValidationException`.

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

Example response (422):

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

## 3. Validating a single field

`ValidationException.single()` raises in one line.

```python
from nene2.validation import ValidationException

raise ValidationException.single("email", "Email is required", ValidationCode.REQUIRED)
```

---

## 4. Paths for nested fields

Pass the path of a nested field as a dot-separated string (there is no
normalization helper).

```python
ValidationError("address.city", "Required", ValidationCode.REQUIRED)
ValidationError("items.0.quantity", "Enter 1 or more", ValidationCode.OUT_OF_RANGE)
```

---

## 5. A @model_validator error has field "request"

When you `raise ValueError(...)` in a Pydantic `@model_validator(mode="after")`,
`loc` is an empty tuple. nene2's `ValidationException` conversion maps this to
`field: "request"`.

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

Example response (422):

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

On the frontend, treat `field: "request"` as an error for the whole form, and
include the relevant field name in the error message text.

---

## 6. Integration with ErrorHandlerMiddleware

Adding `nene2.middleware.ErrorHandlerMiddleware` to the app converts a
`ValidationException` into a 422 Problem Details response automatically.

```python
from nene2.middleware import ErrorHandlerMiddleware

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)
```

---

## 7. Return 400 for failures decoding external input

With Pydantic's `Query()` / `Body()`, a type-conversion failure becomes a 422. But
for things you "receive as a string and decode yourself" — cursors (Base64),
tokens, etc. — if you don't catch the decode exception, `ErrorHandlerMiddleware`
returns it as a 500.

```python
from fastapi.responses import JSONResponse

@app.get("/posts")
def list_posts(after: str | None = Query(None)) -> JSONResponse:
    if after is not None:
        try:
            cursor_id = _decode_cursor(after)  # e.g. base64.urlsafe_b64decode
        except Exception:
            return JSONResponse({"detail": "Invalid cursor"}, status_code=400)
        # continue using cursor_id
```

Catch decode failures such as `binascii.Error` together via `ValueError` /
`Exception` and return `400 Bad Request` — this is user input error, not a server
error.
