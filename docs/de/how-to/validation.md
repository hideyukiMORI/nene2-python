# How-to: Validierungsfehler behandeln

So geben Sie Domain-Validierungsfehler an den Client zurück mit `ValidationException` und `ValidationError` aus `nene2.validation`.

---

## 1. ValidationCode als StrEnum definieren

Das Framework definiert keine Standard-Fehlercodes. Definieren Sie diese pro Projekt mit einem `StrEnum`.

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

Ein `StrEnum` zu verwenden:
- kann direkt an den `ValidationError`-Konstruktor übergeben werden (typsicher)
- serialisiert zu seinem String-Wert in JSON
- ermöglicht IDE-Vervollständigung und statische Analyse

---

## 2. Mehrere Felder validieren

Fehler in einer Liste akkumulieren und eine einzelne `ValidationException` auslösen.

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

Beispielantwort (422):

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

## 3. Ein einzelnes Feld validieren

`ValidationException.single()` löst in einer Zeile aus.

```python
from nene2.validation import ValidationException

raise ValidationException.single("email", "Email is required", ValidationCode.REQUIRED)
```

---

## 4. Pfade für verschachtelte Felder

Übergeben Sie den Pfad eines verschachtelten Felds als durch Punkte getrennten String (es gibt keinen Normalisierungshelfer).

```python
ValidationError("address.city", "Required", ValidationCode.REQUIRED)
ValidationError("items.0.quantity", "Enter 1 or more", ValidationCode.OUT_OF_RANGE)
```

---

## 5. Ein @model_validator-Fehler hat das Feld "request"

Wenn Sie `raise ValueError(...)` in einem Pydantic-`@model_validator(mode="after")` auslösen, ist `loc` ein leeres Tupel. nene2s `ValidationException`-Konvertierung ordnet dies `field: "request"` zu.

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

Beispielantwort (422):

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

Im Frontend behandeln Sie `field: "request"` als Fehler für das gesamte Formular und fügen den relevanten Feldnamen in den Fehlermeldungstext ein.

---

## 6. Integration mit ErrorHandlerMiddleware

Das Hinzufügen von `nene2.middleware.ErrorHandlerMiddleware` zur App wandelt eine `ValidationException` automatisch in eine 422 Problem Details-Antwort um.

```python
from nene2.middleware import ErrorHandlerMiddleware

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)
```

---

## 7. 400 bei Fehlern beim Dekodieren externer Eingaben zurückgeben

Mit Pydantics `Query()` / `Body()` wird ein Typkonvertierungsfehler zu 422. Aber für Dinge, die Sie "als String empfangen und selbst dekodieren" — Cursor (Base64), Tokens, usw. — gibt `ErrorHandlerMiddleware` sie als 500 zurück, wenn Sie die Dekodierungsausnahme nicht abfangen.

```python
from fastapi.responses import JSONResponse

@app.get("/posts")
def list_posts(after: str | None = Query(None)) -> JSONResponse:
    if after is not None:
        try:
            cursor_id = _decode_cursor(after)  # z. B. base64.urlsafe_b64decode
        except Exception:
            return JSONResponse({"detail": "Invalid cursor"}, status_code=400)
        # mit cursor_id fortfahren
```

Fangen Sie Dekodierungsfehler wie `binascii.Error` zusammen über `ValueError` / `Exception` ab und geben Sie `400 Bad Request` zurück — dies ist ein Benutzereingabefehler, kein Serverfehler.
