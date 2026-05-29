# Como fazer: RFC 9457 Problem Details

## Uso básico

`problem_details_response()` é uma factory que retorna uma resposta de erro JSON compatível com RFC 9457.

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

Exemplo de resposta:

```json
{
  "type": "https://nene2.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Article ID 42 does not exist",
  "article_id": 42
}
```

O Content-Type é definido como `application/problem+json` automaticamente.

---

## Definir um base_url para todo o projeto

Para mudar o `base_url` padrão (`https://nene2.dev/problems/`) para uma URL
específica do projeto, chame `configure_problem_details()` uma vez na inicialização do app.

```python
# Na factory da aplicação, ex: app.py
from nene2.http import configure_problem_details

configure_problem_details(base_url="https://api.myapp.com/problems/")
```

Depois disso, você não precisa mais passar `base_url` toda vez:

```python
# base_url pode ser omitido nos handlers
return problem_details_response("not-found", "Not Found", 404)
# → type: "https://api.myapp.com/problems/not-found"
```

Para usar um `base_url` diferente em uma chamada específica, passe-o explicitamente para sobrescrever.

---

## Use constantes type-safe para problem_type

`problem_type` é passado como string literal, então um erro de digitação não será capturado pelo mypy.
Gerencie-os de forma type-safe com um `StrEnum` no seu projeto.

```python
from enum import StrEnum

class ProblemType(StrEnum):
    NOT_FOUND = "not-found"
    UNAUTHORIZED = "unauthorized"
    VALIDATION_FAILED = "validation-failed"
    ARTICLE_NOT_FOUND = "article-not-found"
```

Uso:

```python
from nene2.http import problem_details_response
from .problems import ProblemType

return problem_details_response(ProblemType.NOT_FOUND, "Not Found", 404)
```

`StrEnum` é uma subclasse de `str`, então é compatível com o parâmetro `str` de
`problem_details_response()`.

---

## Integração com ErrorHandlerMiddleware

`ErrorHandlerMiddleware` converte automaticamente uma `ValidationException` em um
`problem_details_response()`, então você não precisa tratar manualmente.

```python
# Isso se torna 422 + application/problem+json automaticamente
raise ValidationException.single("title", "Title is required", "required")
```

Resposta:

```json
{
  "type": "https://nene2.dev/problems/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "detail": "The request contains invalid values.",
  "errors": [{"field": "title", "message": "Title is required", "code": "required"}]
}
```
