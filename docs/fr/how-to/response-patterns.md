# Guide pratique : schémas de réponse

Schémas pour retourner des réponses avec FastAPI + nene2.

**Le schéma par défaut est "retourner une instance du modèle de réponse"** (§1). Vous ne
retournez une `JSONResponse` directement que dans des cas particuliers — statut/en-têtes
personnalisés / streaming / mélange succès et erreur (§3 et suivants). L'implémentation de
référence `src/example/*/handler.py` est uniformément celle du premier cas.

---

## 1. Schéma par défaut : retourner une instance du modèle de réponse

Le handler déclare `response_model` et **retourne une instance de ce type**. FastAPI valide
le contenu et le sérialise exactement selon le schéma déclaré (ainsi OpenAPI et le corps de
réponse correspondent).

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class NoteResponse(BaseModel):
    note_id: int = Field(description="Note ID")
    title: str = Field(description="Title")


# ✅ par défaut : retourner l'instance du modèle → FastAPI valide + sérialise
@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int) -> NoteResponse:
    return NoteResponse(note_id=note_id, title="Hello")
```

> ⚠️ Même avec `response_model` défini, **retourner une `JSONResponse` directement ignore la
> validation de son contenu** (`response_model` est utilisé uniquement pour la génération du
> schéma OpenAPI ; le corps est envoyé tel quel). Pour les routes normales, retournez l'instance
> du modèle pour que la validation s'applique. Utilisez `JSONResponse` uniquement pour les cas
> particuliers de §3 et suivants. CLAUDE.md impose aussi "déclarer `response_model` ; pas de
> retours `Any`."

---

## 2. Dataclass de domaine vs. modèle de réponse Pydantic : deux définitions

Dans nene2, la couche domaine et la couche HTTP sont séparées, donc deux classes avec les mêmes
champs apparaissent.

```python
# Couche domaine : dataclass frozen (valeurs de retour DB, I/O du UseCase)
@dataclass(frozen=True, slots=True)
class Note:
    note_id: int
    title: str

# Couche HTTP : modèle Pydantic (génération de schéma OpenAPI, validation)
class NoteResponse(BaseModel):
    note_id: int = Field(description="Note ID")
    title: str = Field(description="Title")
```

**Pourquoi deux ?** Un `dataclass` est un objet valeur exprimant les invariants du domaine ;
un `Pydantic BaseModel` est la définition de sérialisation/schéma de la frontière HTTP. Ils
ont des responsabilités différentes.

Convertissez explicitement dans le handler et **retournez l'instance du modèle** (le schéma
par défaut du §1) :

```python
@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int) -> NoteResponse:
    note = get_use_case.execute(GetNoteInput(note_id))
    return NoteResponse(note_id=note.note_id, title=note.title)
```

---

## 3. Mélanger problem_details_response() et JSONResponse

Quand le même endpoint retourne une `JSONResponse` en cas de succès et une
`problem_details_response()` en cas d'erreur, les types de retour diffèrent. Les deux sont des
instances ou sous-classes de `JSONResponse`, donc le type de retour peut être unifié comme
`JSONResponse`.

```python
@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int) -> JSONResponse:
    if note_id not in _notes:
        return problem_details_response("not-found", "Not Found", 404, "Note not found.")
    return JSONResponse({"note_id": note_id, "title": "Hello"})
```

---

## 4. Le paramètre `response: Response` est incompatible avec JSONResponse

Ajouter des en-têtes via le paramètre `response: Response` de FastAPI et retourner une
`JSONResponse` directement **ne peuvent pas être mélangés**.

```python
# ❌ les en-têtes définis via response: Response ne sont pas reflétés dans une JSONResponse
@app.get("/items/{item_id}")
def get_item(item_id: int, response: Response) -> JSONResponse:
    response.headers["X-Custom"] = "value"  # sans effet
    return JSONResponse({"item_id": item_id})

# ✅ passer les en-têtes directement à JSONResponse
@app.get("/items/{item_id}")
def get_item(item_id: int) -> JSONResponse:
    return JSONResponse({"item_id": item_id}, headers={"X-Custom": "value"})
```

Le paramètre `response: Response` ne fonctionne que quand FastAPI génère automatiquement l'objet
réponse (c'est-à-dire quand vous retournez un `dict`).

---

## 5. Passer `mode="json"` quand on donne model_dump() à JSONResponse

Quand vous passez `model_dump()` directement à `JSONResponse`, les objets Python comme
`datetime` ne peuvent pas être sérialisés par `json.dumps` et vous obtenez une erreur 500.
Spécifier `mode="json"` fait que Pydantic convertit en types compatibles JSON.

```python
from pydantic import BaseModel
from datetime import datetime

class OrderLine(BaseModel):
    created_at: datetime
    quantity: int

line = OrderLine(created_at=datetime(2026, 1, 1), quantity=3)

# ❌ TypeError: Object of type datetime is not JSON serializable
return JSONResponse(line.model_dump())

# ✅ mode="json" convertit datetime → chaîne ISO 8601
return JSONResponse(line.model_dump(mode="json"))
```

**Quand cela pose problème** : les routes normales utilisant `response_model=` s'en sortent
bien car FastAPI convertit automatiquement. Faites attention aux routes qui retournent
`JSONResponse` directement (207 Multi-Status, réponses personnalisées, `/preview` contenant des
modèles imbriqués, etc.).

---

## 6. 204 No Content et response_model

Spécifier `response_model` sur un endpoint `204 No Content` provoque une erreur d'assertion
FastAPI.

```python
# ❌ response_model ne peut pas être spécifié avec 204
@app.delete("/notes/{note_id}", status_code=204, response_model=SomeModel)
def delete_note(note_id: int) -> None: ...

# ✅ omettre response_model
@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int) -> None: ...
```
