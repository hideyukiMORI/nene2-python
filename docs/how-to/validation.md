# How-to: バリデーションエラーを扱う

`nene2.validation` の `ValidationException` と `ValidationError` を使って、
ドメインバリデーションエラーをクライアントに返す方法を説明する。

---

## 1. ValidationCode を StrEnum で定義する

フレームワークは標準エラーコードを定義しない。プロジェクトごとに `StrEnum` で定義する。

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

`StrEnum` を使うと:
- `ValidationError` コンストラクタに直接渡せる（型安全）
- JSON シリアライズ時に文字列値として出力される
- IDE の補完・静的解析が効く

---

## 2. 複数フィールドのバリデーション

リストにエラーを積み上げて `ValidationException` をまとめて raise する。

```python
from nene2.validation import ValidationError, ValidationException

def validate_registration(username: str, email: str, age: int) -> None:
    errors: list[ValidationError] = []

    if len(username) < 3:
        errors.append(ValidationError("username", "3文字以上必要です", ValidationCode.TOO_SHORT))
    if "@" not in email:
        errors.append(ValidationError("email", "有効なメールアドレスを入力してください", ValidationCode.INVALID_FORMAT))
    if age < 0 or age > 150:
        errors.append(ValidationError("age", "年齢は 0〜150 の範囲で入力してください", ValidationCode.OUT_OF_RANGE))

    if errors:
        raise ValidationException(errors)
```

レスポンス例 (422):

```json
{
  "type": "https://example.com/problems/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "errors": [
    {"field": "username", "message": "3文字以上必要です", "code": "too_short"},
    {"field": "email",    "message": "有効なメールアドレスを入力してください", "code": "invalid_format"}
  ]
}
```

---

## 3. 単一フィールドのバリデーション

`ValidationException.single()` で 1 行で raise できる。

```python
from nene2.validation import ValidationException

raise ValidationException.single("email", "メールアドレスは必須です", ValidationCode.REQUIRED)
```

---

## 4. ネストフィールドのパス

ネストしたフィールドのパスはドット区切りの文字列で渡す（正規化ヘルパーはない）。

```python
ValidationError("address.city", "必須です", ValidationCode.REQUIRED)
ValidationError("items.0.quantity", "1 以上を入力してください", ValidationCode.OUT_OF_RANGE)
```

---

## 5. ErrorHandlerMiddleware との連携

`nene2.middleware.ErrorHandlerMiddleware` をアプリに追加すると、
`ValidationException` が自動で 422 Problem Details レスポンスに変換される。

```python
from nene2.middleware import ErrorHandlerMiddleware

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)
```
