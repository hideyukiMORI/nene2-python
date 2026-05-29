# Como fazer: soft delete (deleção lógica)

Um padrão para deleção lógica usando um campo `deleted_at: datetime | None`.

---

## Entidade de domínio

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

A propriedade `is_deleted` mantém a lógica de negócio dentro do domínio, para que os
chamadores não precisem raciocinar sobre `deleted_at is not None`.

---

## Atualizando um dataclass frozen: dataclasses.replace()

```python
from dataclasses import replace

article = replace(article, deleted_at=datetime.now(UTC))
```

Um dataclass `frozen=True` não pode ter seus campos mutados diretamente, mas `replace()`
cria uma nova instância.

---

## Endpoint DELETE (idempotente)

```python
@app.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int) -> None:
    article = _store.get(article_id)
    if article is None or article.is_deleted:
        return  # idempotente: já deletado ou ausente também retorna 204
    _store[article_id] = replace(article, deleted_at=datetime.now(UTC))
```

Conforme o RFC 9110, DELETE é idempotente. Um DELETE contra um recurso ausente ou
já deletado também retorna 204.

---

## Excluindo em list / get

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
    return ArticleResponse.from_domain(article)  # retorne o modelo no sucesso (padrão)
```

---

## Excluindo deleted_at da resposta

Simplesmente não defina um campo `deleted_at` em `ArticleResponse`. O Pydantic não
serializa campos que não estão definidos.

```python
class ArticleResponse(BaseModel):
    article_id: int
    title: str
    # deleted_at não incluído → o detalhe de implementação da deleção lógica não vaza para a API pública
```

Retornar `deleted_at` apenas em endpoints de admin é o design recomendado.

---

## Veja também

- FT110: `docs/field-trials/2026-05-field-trial-110.md`
