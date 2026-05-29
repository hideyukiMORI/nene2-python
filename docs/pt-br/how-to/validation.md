# Como fazer: tratamento de erros de validação

Como retornar erros de validação de domínio para o cliente usando `ValidationException`
e `ValidationError` de `nene2.validation`.

---

## 1. Definir ValidationCode como StrEnum

O framework não define códigos de erro padrão. Defina-os por projeto com um
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

Usar um `StrEnum`:
- pode ser passado diretamente ao construtor de `ValidationError` (type-safe)
- serializa para seu valor string em JSON
- recebe completação de IDE e análise estática

---

## 2. Validando múltiplos campos

Acumule erros em uma lista e levante uma única `ValidationException`.

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

Exemplo de resposta (422):

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

## 3. Validando um único campo

`ValidationException.single()` levanta em uma linha.

```python
from nene2.validation import ValidationException

raise ValidationException.single("email", "Email is required", ValidationCode.REQUIRED)
```

---

## 4. Caminhos para campos aninhados

Passe o caminho de um campo aninhado como string separada por ponto (não há
helper de normalização).

```python
ValidationError("address.city", "Required", ValidationCode.REQUIRED)
ValidationError("items.0.quantity", "Enter 1 or more", ValidationCode.OUT_OF_RANGE)
```

---

## 5. Um erro @model_validator tem field "request"

Quando você lança `ValueError(...)` em um `@model_validator(mode="after")` do Pydantic,
`loc` é uma tupla vazia. A conversão de `ValidationException` do nene2 mapeia isso para
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

Exemplo de resposta (422):

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

No frontend, trate `field: "request"` como um erro para o formulário inteiro, e
inclua o nome do campo relevante no texto da mensagem de erro.

---

## 6. Integração com ErrorHandlerMiddleware

Adicionar `nene2.middleware.ErrorHandlerMiddleware` ao app converte uma
`ValidationException` em uma resposta 422 Problem Details automaticamente.

```python
from nene2.middleware import ErrorHandlerMiddleware

app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)
```

---

## 7. Retorne 400 para falhas ao decodificar entrada externa

Com `Query()` / `Body()` do Pydantic, uma falha de conversão de tipo vira um 422. Mas
para coisas que você "recebe como string e decodifica você mesmo" — cursores (Base64),
tokens, etc. — se você não capturar a exceção de decodificação, `ErrorHandlerMiddleware`
a retorna como um 500.

```python
from fastapi.responses import JSONResponse

@app.get("/posts")
def list_posts(after: str | None = Query(None)) -> JSONResponse:
    if after is not None:
        try:
            cursor_id = _decode_cursor(after)  # ex: base64.urlsafe_b64decode
        except Exception:
            return JSONResponse({"detail": "Invalid cursor"}, status_code=400)
        # continue usando cursor_id
```

Capture falhas de decodificação como `binascii.Error` junto via `ValueError` /
`Exception` e retorne `400 Bad Request` — isso é erro de entrada do usuário, não um erro do servidor.
