# Guide pratique : suppression douce (suppression logique)

Un schéma pour la suppression logique en utilisant un champ `deleted_at: datetime | None`.

---

## Entité de domaine

```python
from dataclasses import dataclass
from datetime import UTC, datetime

@dataclass(frozen=True, slots=True)
class Article:
    article_id: int
    title: str
    deleted_at: datetime | None = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

La propriété `is_deleted` garde la logique métier dans le domaine, de sorte que les appelants
n'ont pas à raisonner sur `deleted_at is not None`.

---

## Mettre à jour un dataclass frozen : dataclasses.replace()

```python
from dataclasses import replace

article = replace(article, deleted_at=datetime.now(UTC))
```

Un dataclass `frozen=True` ne peut pas avoir ses champs mutés directement, mais `replace()`
crée une nouvelle instance.

---

## Endpoint DELETE (idempotent)

```python
@app.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int) -> None:
    article = _store.get(article_id)
    if article is None or article.is_deleted:
        return  # idempotent : déjà supprimé ou manquant retourne aussi 204
    _store[article_id] = replace(article, deleted_at=datetime.now(UTC))
```

Selon la RFC 9110, DELETE est idempotent. Un DELETE sur une ressource manquante ou déjà
supprimée retourne aussi 204.

---

## Exclusion dans les listes / lecture unitaire

```python
def _active_articles() -> list[Article]:
    return [a for a in _store.values() if not a.is_deleted]

@app.get("/articles", response_model=list[ArticleResponse])
def list_articles() -> list[ArticleResponse]:
    return [ArticleResponse.from_domain(a) for a in _active_articles()]

@app.get("/articles/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int) -> ArticleResponse | JSONResponse:
    article = _store.get(article_id)
    if article is None or article.is_deleted:
        return problem_details_response("not-found", "Not Found", 404, "Article not found.")
    return ArticleResponse.from_domain(article)  # retourner le modèle en cas de succès (schéma par défaut)
```

---

## Exclure deleted_at de la réponse

Ne définissez simplement pas de champ `deleted_at` sur `ArticleResponse`. Pydantic ne sérialise
pas les champs qui ne sont pas définis.

```python
class ArticleResponse(BaseModel):
    article_id: int
    title: str
    # deleted_at non inclus → le détail d'implémentation de la suppression logique ne fuit pas dans l'API publique
```

Retourner `deleted_at` uniquement dans les endpoints admin est la conception recommandée.

---

## Voir aussi

- FT110 : `docs/field-trials/2026-05-field-trial-110.md`
