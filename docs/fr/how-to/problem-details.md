# Guide pratique : RFC 9457 Problem Details

## Utilisation de base

`problem_details_response()` est une factory qui retourne une réponse JSON d'erreur conforme
à la RFC 9457.

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

Exemple de réponse :

```json
{
  "type": "https://nene2.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Article ID 42 does not exist",
  "article_id": 42
}
```

Le Content-Type est automatiquement défini à `application/problem+json`.

---

## Définir une base_url pour tout le projet

Pour changer la `base_url` par défaut (`https://nene2.dev/problems/`) par une URL spécifique
au projet, appelez `configure_problem_details()` une fois au démarrage de l'application.

```python
# Dans la factory d'application, p. ex. app.py
from nene2.http import configure_problem_details

configure_problem_details(base_url="https://api.myapp.com/problems/")
```

Ensuite, vous n'avez plus à passer `base_url` à chaque fois :

```python
# base_url peut être omis dans les handlers
return problem_details_response("not-found", "Not Found", 404)
# → type: "https://api.myapp.com/problems/not-found"
```

Pour utiliser une `base_url` différente pour un appel spécifique, passez-la explicitement pour
la surcharger.

---

## Utiliser des constantes typées pour problem_type

`problem_type` est passé comme une chaîne littérale, donc une faute de frappe ne sera pas
détectée par mypy. Gérez-les de façon typée avec un `StrEnum` dans votre projet.

```python
from enum import StrEnum

class ProblemType(StrEnum):
    NOT_FOUND = "not-found"
    UNAUTHORIZED = "unauthorized"
    VALIDATION_FAILED = "validation-failed"
    ARTICLE_NOT_FOUND = "article-not-found"
```

Utilisation :

```python
from nene2.http import problem_details_response
from .problems import ProblemType

return problem_details_response(ProblemType.NOT_FOUND, "Not Found", 404)
```

`StrEnum` est une sous-classe de `str`, donc il est compatible avec le paramètre `str` de
`problem_details_response()`.

---

## Intégration avec ErrorHandlerMiddleware

`ErrorHandlerMiddleware` convertit automatiquement une `ValidationException` en
`problem_details_response()`, donc vous n'avez pas besoin de la gérer manuellement.

```python
# Cela devient automatiquement 422 + application/problem+json
raise ValidationException.single("title", "Title is required", "required")
```

Réponse :

```json
{
  "type": "https://nene2.dev/problems/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "detail": "The request contains invalid values.",
  "errors": [{"field": "title", "message": "Title is required", "code": "required"}]
}
```
