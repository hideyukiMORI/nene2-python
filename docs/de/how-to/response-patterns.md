# How-to: Antwortmuster

Muster für Antworten mit FastAPI + nene2.

**Der Standard ist "eine Instanz des Antwortmodells zurückgeben"** (§1). Sie geben `JSONResponse` nur in Sonderfällen von Hand zurück — benutzerdefinierter Status / Header / Streaming / Mischen von Erfolg und Fehler (§3 und folgende). Die Referenzimplementierung `src/example/*/handler.py` verwendet einheitlich Ersteres.

---

## 1. Standardmuster: eine Antwortmodell-Instanz zurückgeben

Der Handler deklariert `response_model` und **gibt eine Instanz dieses Typs zurück**. FastAPI validiert den Inhalt und serialisiert ihn genau gemäß dem deklarierten Schema (sodass OpenAPI und Antwort-Body übereinstimmen).

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class NoteResponse(BaseModel):
    note_id: int = Field(description="Note ID")
    title: str = Field(description="Title")


# ✅ Standard: Modell-Instanz zurückgeben → FastAPI validiert + serialisiert
@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int) -> NoteResponse:
    return NoteResponse(note_id=note_id, title="Hello")
```

> ⚠️ Auch wenn `response_model` gesetzt ist, **überspringt das direkte Zurückgeben einer `JSONResponse` die Validierung ihres Inhalts** (`response_model` wird nur für die OpenAPI-Schema-Generierung verwendet; der Body wird so gesendet wie er ist). Geben Sie für normale Routen die Modell-Instanz zurück, damit die Validierung greift. Verwenden Sie `JSONResponse` nur für die Sonderfälle in §3 und folgendem. CLAUDE.md schreibt außerdem vor: "declare `response_model`; no `Any` returns."

---

## 2. Domain-Dataclass vs. Pydantic-Antwortmodell: zwei Definitionen

In nene2 sind Domain-Schicht und HTTP-Schicht getrennt, daher erscheinen zwei Klassen mit denselben Feldern.

```python
# Domain-Schicht: frozen dataclass (DB-Rückgabewerte, UseCase-I/O)
@dataclass(frozen=True, slots=True)
class Note:
    note_id: int
    title: str

# HTTP-Schicht: Pydantic-Modell (OpenAPI-Schema-Generierung, Validierung)
class NoteResponse(BaseModel):
    note_id: int = Field(description="Note ID")
    title: str = Field(description="Title")
```

**Warum zwei?** Ein `dataclass` ist ein Wertobjekt, das Domain-Invarianten ausdrückt; ein Pydantic-`BaseModel` ist die HTTP-Grenz-Serialisierungs-/Schema-Definition. Sie haben unterschiedliche Verantwortlichkeiten.

Wandeln Sie explizit im Handler um und **geben Sie die Modell-Instanz zurück** (das Standardmuster aus §1):

```python
@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int) -> NoteResponse:
    note = get_use_case.execute(GetNoteInput(note_id))
    return NoteResponse(note_id=note.note_id, title=note.title)
```

---

## 3. problem_details_response() und JSONResponse mischen

Wenn derselbe Endpunkt bei Erfolg `JSONResponse` und bei Fehler `problem_details_response()` zurückgibt, unterscheiden sich die Rückgabetypen. Beide sind Instanzen oder Unterklassen von `JSONResponse`, daher kann der Rückgabetyp als `JSONResponse` vereinheitlicht werden.

```python
@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int) -> JSONResponse:
    if note_id not in _notes:
        return problem_details_response("not-found", "Not Found", 404, "Note not found.")
    return JSONResponse({"note_id": note_id, "title": "Hello"})
```

---

## 4. Der `response: Response`-Parameter ist inkompatibel mit JSONResponse

Das Hinzufügen von Headern über FastAPIs `response: Response`-Parameter und das direkte Zurückgeben einer `JSONResponse` **kann nicht kombiniert werden**.

```python
# ❌ über response: Response gesetzte Header werden in einer JSONResponse nicht reflektiert
@app.get("/items/{item_id}")
def get_item(item_id: int, response: Response) -> JSONResponse:
    response.headers["X-Custom"] = "value"  # hat keinen Effekt
    return JSONResponse({"item_id": item_id})

# ✅ Header direkt an JSONResponse übergeben
@app.get("/items/{item_id}")
def get_item(item_id: int) -> JSONResponse:
    return JSONResponse({"item_id": item_id}, headers={"X-Custom": "value"})
```

Der `response: Response`-Parameter funktioniert nur, wenn FastAPI das Antwortobjekt automatisch generiert (d. h. wenn Sie ein `dict` zurückgeben).

---

## 5. `mode="json"` beim Übergeben von model_dump() an JSONResponse angeben

Wenn Sie `model_dump()` direkt an `JSONResponse` übergeben, können Python-Objekte wie `datetime` nicht von `json.dumps` serialisiert werden und Sie erhalten einen 500-Fehler. Die Angabe von `mode="json"` lässt Pydantic in JSON-kompatible Typen umwandeln.

```python
from pydantic import BaseModel
from datetime import datetime

class OrderLine(BaseModel):
    created_at: datetime
    quantity: int

line = OrderLine(created_at=datetime(2026, 1, 1), quantity=3)

# ❌ TypeError: Object of type datetime is not JSON serializable
return JSONResponse(line.model_dump())

# ✅ mode="json" wandelt datetime → ISO-8601-String um
return JSONResponse(line.model_dump(mode="json"))
```

**Wann das zum Problem wird**: Normale Routen mit `response_model=` sind in Ordnung, da FastAPI automatisch umwandelt. Achten Sie auf Routen, die `JSONResponse` direkt zurückgeben (207 Multi-Status, benutzerdefinierte Antworten, ein `/preview` mit verschachtelten Modellen, usw.).

---

## 6. 204 No Content und response_model

Das Angeben von `response_model` auf einem `204 No Content`-Endpunkt verursacht einen FastAPI-Assertion-Fehler.

```python
# ❌ response_model kann bei 204 nicht angegeben werden
@app.delete("/notes/{note_id}", status_code=204, response_model=SomeModel)
def delete_note(note_id: int) -> None: ...

# ✅ response_model weglassen
@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int) -> None: ...
```
