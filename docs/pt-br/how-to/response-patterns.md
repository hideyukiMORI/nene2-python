# Como fazer: padrões de resposta

Padrões para retornar respostas com FastAPI + nene2.

**O padrão padrão é "retornar uma instância do modelo de resposta"** (§1). Você retorna um
`JSONResponse` manualmente apenas em casos especiais — status / headers customizados /
streaming / misturar sucesso e erro (§3 em diante). A implementação de referência
`src/example/*/handler.py` é uniformemente a primeira.

---

## 1. Padrão padrão: retornar uma instância do modelo de resposta

O handler declara `response_model` e **retorna uma instância desse tipo**.
O FastAPI valida o conteúdo e serializa exatamente conforme o schema declarado
(então o OpenAPI e o corpo da resposta coincidem).

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class NoteResponse(BaseModel):
    note_id: int = Field(description="Note ID")
    title: str = Field(description="Title")


# ✅ padrão: retornar a instância do modelo → FastAPI valida + serializa
@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int) -> NoteResponse:
    return NoteResponse(note_id=note_id, title="Hello")
```

> ⚠️ Mesmo com `response_model` definido, **retornar um `JSONResponse` diretamente pula
> a validação do seu conteúdo** (`response_model` é usado apenas para geração do schema OpenAPI;
> o corpo é enviado como está). Para rotas normais, retorne a instância do modelo para que a
> validação seja aplicada. Use `JSONResponse` apenas para os casos especiais em §3 em diante.
> O CLAUDE.md também exige "declare `response_model`; sem retornos `Any`."

---

## 2. Dataclass de domínio vs. modelo de resposta Pydantic: duas definições

No nene2, a camada de domínio e a camada HTTP são separadas, então duas classes com os
mesmos campos aparecem.

```python
# Camada de domínio: dataclass frozen (valores de retorno do DB, I/O do UseCase)
@dataclass(frozen=True, slots=True)
class Note:
    note_id: int
    title: str

# Camada HTTP: modelo Pydantic (geração de schema OpenAPI, validação)
class NoteResponse(BaseModel):
    note_id: int = Field(description="Note ID")
    title: str = Field(description="Title")
```

**Por que dois?** Um `dataclass` é um objeto de valor que expressa invariantes de domínio; um
`Pydantic BaseModel` é a definição de serialização/schema na fronteira HTTP. Eles têm
responsabilidades diferentes.

Converta explicitamente no handler e **retorne a instância do modelo** (o padrão padrão do §1):

```python
@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int) -> NoteResponse:
    note = get_use_case.execute(GetNoteInput(note_id))
    return NoteResponse(note_id=note.note_id, title=note.title)
```

---

## 3. Misturando problem_details_response() e JSONResponse

Quando o mesmo endpoint retorna um `JSONResponse` no sucesso e um
`problem_details_response()` no erro, os tipos de retorno diferem. Ambos são instâncias
ou subclasses de `JSONResponse`, então o tipo de retorno pode ser unificado como
`JSONResponse`.

```python
@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int) -> JSONResponse:
    if note_id not in _notes:
        return problem_details_response("not-found", "Not Found", 404, "Note not found.")
    return JSONResponse({"note_id": note_id, "title": "Hello"})
```

---

## 4. O parâmetro `response: Response` é incompatível com JSONResponse

Adicionar headers via o parâmetro `response: Response` do FastAPI e retornar um
`JSONResponse` diretamente **não pode ser misturado**.

```python
# ❌ headers definidos via response: Response não são refletidos em um JSONResponse
@app.get("/items/{item_id}")
def get_item(item_id: int, response: Response) -> JSONResponse:
    response.headers["X-Custom"] = "value"  # sem efeito
    return JSONResponse({"item_id": item_id})

# ✅ passe headers diretamente para JSONResponse
@app.get("/items/{item_id}")
def get_item(item_id: int) -> JSONResponse:
    return JSONResponse({"item_id": item_id}, headers={"X-Custom": "value"})
```

O parâmetro `response: Response` só funciona quando o FastAPI gera automaticamente o
objeto de resposta (ou seja, quando você retorna um `dict`).

---

## 5. Passe `mode="json"` ao passar model_dump() para JSONResponse

Quando você passa `model_dump()` diretamente para `JSONResponse`, objetos Python como
`datetime` não podem ser serializados por `json.dumps` e você recebe um 500. Especificar
`mode="json"` faz o Pydantic converter para tipos compatíveis com JSON.

```python
from pydantic import BaseModel
from datetime import datetime

class OrderLine(BaseModel):
    created_at: datetime
    quantity: int

line = OrderLine(created_at=datetime(2026, 1, 1), quantity=3)

# ❌ TypeError: Object of type datetime is not JSON serializable
return JSONResponse(line.model_dump())

# ✅ mode="json" converte datetime → string ISO 8601
return JSONResponse(line.model_dump(mode="json"))
```

**Quando isso causa problemas**: rotas normais usando `response_model=` estão ok porque
o FastAPI converte automaticamente. Fique atento em rotas que retornam `JSONResponse`
diretamente (207 Multi-Status, respostas customizadas, um `/preview` contendo modelos aninhados, etc.).

---

## 6. 204 No Content e response_model

Especificar `response_model` em um endpoint `204 No Content` causa um erro de asserção no FastAPI.

```python
# ❌ response_model não pode ser especificado com 204
@app.delete("/notes/{note_id}", status_code=204, response_model=SomeModel)
def delete_note(note_id: int) -> None: ...

# ✅ omita response_model
@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int) -> None: ...
```
