# How-to: RFC 9457 Problem Details

## Grundlegende Verwendung

`problem_details_response()` ist eine Factory, die eine RFC-9457-konforme JSON-Fehlerantwort zurückgibt.

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

Beispielantwort:

```json
{
  "type": "https://nene2.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Article ID 42 does not exist",
  "article_id": 42
}
```

Der Content-Type wird automatisch auf `application/problem+json` gesetzt.

---

## Projektweite base_url festlegen

Um die Standard-`base_url` (`https://nene2.dev/problems/`) auf eine projektspezifische URL zu ändern, rufen Sie `configure_problem_details()` einmal beim App-Start auf.

```python
# In der Anwendungsfactory, z. B. app.py
from nene2.http import configure_problem_details

configure_problem_details(base_url="https://api.myapp.com/problems/")
```

Danach müssen Sie `base_url` nicht mehr bei jedem Aufruf angeben:

```python
# base_url kann in Handlern weggelassen werden
return problem_details_response("not-found", "Not Found", 404)
# → type: "https://api.myapp.com/problems/not-found"
```

Um eine andere `base_url` für einen bestimmten Aufruf zu verwenden, übergeben Sie sie explizit zur Überschreibung.

---

## Typsichere Konstanten für problem_type verwenden

`problem_type` wird als String-Literal übergeben, daher wird ein Tippfehler nicht von mypy erkannt. Verwalten Sie diese typsicher mit einem `StrEnum` in Ihrem Projekt.

```python
from enum import StrEnum

class ProblemType(StrEnum):
    NOT_FOUND = "not-found"
    UNAUTHORIZED = "unauthorized"
    VALIDATION_FAILED = "validation-failed"
    ARTICLE_NOT_FOUND = "article-not-found"
```

Verwendung:

```python
from nene2.http import problem_details_response
from .problems import ProblemType

return problem_details_response(ProblemType.NOT_FOUND, "Not Found", 404)
```

`StrEnum` ist eine Unterklasse von `str`, daher ist es mit dem `str`-Parameter von `problem_details_response()` kompatibel.

---

## Integration mit ErrorHandlerMiddleware

`ErrorHandlerMiddleware` wandelt eine `ValidationException` automatisch in eine `problem_details_response()` um, sodass Sie sie nicht manuell behandeln müssen.

```python
# Dies wird automatisch zu 422 + application/problem+json
raise ValidationException.single("title", "Title is required", "required")
```

Antwort:

```json
{
  "type": "https://nene2.dev/problems/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "detail": "The request contains invalid values.",
  "errors": [{"field": "title", "message": "Title is required", "code": "required"}]
}
```
