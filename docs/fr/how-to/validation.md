# Guide pratique : gérer les erreurs de validation

Comment retourner des erreurs de validation de domaine au client en utilisant
`ValidationException` et `ValidationError` depuis `nene2.validation`.

---

## 1. Définir ValidationCode comme un StrEnum

Le framework ne définit pas de codes d'erreur standard. Définissez-les par projet avec un
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

Utiliser un `StrEnum` :
- peut être passé directement au constructeur de `ValidationError` (typé de façon sûre)
- se sérialise en sa valeur de chaîne dans JSON
- bénéficie de la complétion IDE et de l'analyse statique

---

## 2. Valider plusieurs champs

Accumulez les erreurs dans une liste et levez une seule `ValidationException`.

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

Exemple de réponse (422) :

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

## 3. Valider un seul champ

`ValidationException.single()` lève en une seule ligne.

```python
from nene2.validation import ValidationException

raise ValidationException.single("email", "Email is required", ValidationCode.REQUIRED)
```

---

## 4. Chemins pour les champs imbriqués

Passez le chemin d'un champ imbriqué comme une chaîne séparée par des points (il n'y a pas
de helper de normalisation).

```python
ValidationError("address.city", "Required", ValidationCode.REQUIRED)
ValidationError("items.0.quantity", "Enter 1 or more", ValidationCode.OUT_OF_RANGE)
```

---

## 5. Une erreur @model_validator a le champ "request"

Quand vous levez `ValueError(...)` dans un `@model_validator(mode="after")` Pydantic,
`loc` est un tuple vide. La conversion `ValidationException` de nene2 le mappe vers
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

Exemple de réponse (422) :

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

Côté frontend, traitez `field: "request"` comme une erreur pour tout le formulaire, et incluez
le nom du champ pertinent dans le texte du message d'erreur.

---

## 6. Intégration avec ErrorHandlerMiddleware

Ajouter `nene2.middleware.ErrorHandlerMiddleware` à l'application convertit une
`ValidationException` en réponse 422 Problem Details automatiquement.

```python
from nene2.middleware import ErrorHandlerMiddleware

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)
```

---

## 7. Retourner 400 pour les échecs de décodage d'entrées externes

Avec `Query()` / `Body()` de Pydantic, un échec de conversion de type devient un 422. Mais
pour les choses que vous "recevez comme une chaîne et décodez vous-même" — curseurs (Base64),
tokens, etc. — si vous n'attrapez pas l'exception de décodage, `ErrorHandlerMiddleware` la
retourne comme un 500.

```python
from fastapi.responses import JSONResponse

@app.get("/posts")
def list_posts(after: str | None = Query(None)) -> JSONResponse:
    if after is not None:
        try:
            cursor_id = _decode_cursor(after)  # p. ex. base64.urlsafe_b64decode
        except Exception:
            return JSONResponse({"detail": "Invalid cursor"}, status_code=400)
        # continuer en utilisant cursor_id
```

Capturez les échecs de décodage comme `binascii.Error` ensemble via `ValueError` /
`Exception` et retournez `400 Bad Request` — c'est une erreur d'entrée utilisateur, pas une
erreur serveur.
