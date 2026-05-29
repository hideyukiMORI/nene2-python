# How-to: Soft Delete (logisches Löschen)

Ein Muster für logisches Löschen mit einem `deleted_at: datetime | None`-Feld.

---

## Domain-Entity

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

Die `is_deleted`-Property hält die Geschäftslogik in der Domain, sodass Aufrufer nicht über `deleted_at is not None` nachdenken müssen.

---

## Einen frozen dataclass aktualisieren: dataclasses.replace()

```python
from dataclasses import replace

article = replace(article, deleted_at=datetime.now(UTC))
```

Ein `frozen=True`-Dataclass kann seine Felder nicht direkt mutiert haben, aber `replace()` erstellt eine neue Instanz.

---

## DELETE-Endpunkt (idempotent)

```python
@app.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int) -> None:
    article = _store.get(article_id)
    if article is None or article.is_deleted:
        return  # idempotent: bereits gelöscht oder nicht vorhanden gibt auch 204 zurück
    _store[article_id] = replace(article, deleted_at=datetime.now(UTC))
```

Gemäß RFC 9110 ist DELETE idempotent. Ein DELETE gegen eine fehlende oder bereits gelöschte Ressource gibt ebenfalls 204 zurück.

---

## Bei Auflistung / Abruf ausschließen

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
    return ArticleResponse.from_domain(article)  # bei Erfolg das Modell zurückgeben (Standardmuster)
```

---

## deleted_at aus der Antwort ausschließen

Definieren Sie einfach kein `deleted_at`-Feld in `ArticleResponse`. Pydantic serialisiert keine Felder, die nicht definiert sind.

```python
class ArticleResponse(BaseModel):
    article_id: int
    title: str
    # deleted_at nicht enthalten → das logische Lösch-Implementierungsdetail leckt nicht in die öffentliche API
```

`deleted_at` nur in Admin-Endpunkten zurückzugeben ist das empfohlene Design.

---

## Siehe auch

- FT110: `docs/field-trials/2026-05-field-trial-110.md`
