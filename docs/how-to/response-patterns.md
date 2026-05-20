# How-to: レスポンスパターン

FastAPI + nene2 でのレスポンス返却パターンをまとめる。

---

## 1. JSONResponse + response_model の正しい組み合わせ

`response_model` を指定したエンドポイントで `JSONResponse` を直接返すと、FastAPI はその内容を **バリデーションしない**。`response_model` は OpenAPI スキーマ生成にのみ使われる。

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

class NoteResponse(BaseModel):
    note_id: int
    title: str

# ✅ response_model はスキーマのみ。JSONResponse の内容は直接送られる
@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int) -> JSONResponse:
    return JSONResponse({"note_id": note_id, "title": "Hello"})
```

`response_model` を指定しない場合は `dict | list` を返せるが、OpenAPI スキーマが `{}` になる。スキーマを正確に出力したい場合は常に `response_model` を指定する。

---

## 2. Domain dataclass と Pydantic レスポンスモデルの二重定義

nene2 ではドメイン層と HTTP 層を分離するため、同じフィールドを持つクラスが 2 つ生まれる。

```python
# ドメイン層: frozen dataclass（DB 返却値・UseCase の入出力）
@dataclass(frozen=True, slots=True)
class Note:
    note_id: int
    title: str

# HTTP 層: Pydantic モデル（OpenAPI スキーマ生成・バリデーション）
class NoteResponse(BaseModel):
    note_id: int = Field(description="ノート ID")
    title: str = Field(description="タイトル")
```

**なぜ二重になるか**: `dataclass` はドメインの不変条件を表す値オブジェクト、`Pydantic BaseModel` は HTTP 境界のシリアライズ/スキーマ定義。両者は責務が異なる。

変換は手動で行う:

```python
def _note_to_dict(note: Note) -> dict[str, object]:
    return {"note_id": note.note_id, "title": note.title}

@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int) -> JSONResponse:
    note = repository.find(note_id)
    return JSONResponse(_note_to_dict(note))
```

---

## 3. problem_details_response() と JSONResponse の混在

同じエンドポイントで成功時は `JSONResponse`、エラー時は `problem_details_response()` を返す場合、戻り値の型が異なる。どちらも `JSONResponse` のサブクラスまたはインスタンスなので、戻り値型は `JSONResponse` で統一できる。

```python
@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int) -> JSONResponse:
    if note_id not in _notes:
        return problem_details_response("not-found", "Not Found", 404, "Note not found.")
    return JSONResponse({"note_id": note_id, "title": "Hello"})
```

---

## 4. response: Response パラメーターと JSONResponse の非互換

FastAPI で `response: Response` パラメーターを使ってヘッダーを追加するパターンと、`JSONResponse` を直接返すパターンは **混在できない**。

```python
# ❌ response: Response を使ってヘッダーを追加しても JSONResponse には反映されない
@app.get("/items/{item_id}")
def get_item(item_id: int, response: Response) -> JSONResponse:
    response.headers["X-Custom"] = "value"  # 効かない
    return JSONResponse({"item_id": item_id})

# ✅ JSONResponse に直接ヘッダーを渡す
@app.get("/items/{item_id}")
def get_item(item_id: int) -> JSONResponse:
    return JSONResponse({"item_id": item_id}, headers={"X-Custom": "value"})
```

`response: Response` パラメーターは、FastAPI がレスポンスオブジェクトを自動生成する場合（`dict` 返却）にのみ有効。

---

## 5. JSONResponse に model_dump() を渡す場合は mode="json" を使う

`JSONResponse` に直接 `model_dump()` を渡すとき、`datetime` などの Python オブジェクトは
`json.dumps` でシリアライズできず 500 エラーになる。`mode="json"` を指定すると
Pydantic が JSON 互換な型に変換する。

```python
from pydantic import BaseModel
from datetime import datetime

class OrderLine(BaseModel):
    created_at: datetime
    quantity: int

line = OrderLine(created_at=datetime(2026, 1, 1), quantity=3)

# ❌ TypeError: Object of type datetime is not JSON serializable
return JSONResponse(line.model_dump())

# ✅ mode="json" で datetime → ISO 8601 文字列に変換される
return JSONResponse(line.model_dump(mode="json"))
```

**影響が出る場面**: `response_model=` を使う通常ルートは FastAPI が自動変換するため問題ない。
`JSONResponse` を直接返すルート（207 Multi-Status、カスタムレスポンス、ネストモデル含む `/preview` など）
で注意が必要。

---

## 6. 204 No Content と response_model

`204 No Content` のエンドポイントに `response_model` を指定すると FastAPI がアサーションエラーになる。

```python
# ❌ 204 に response_model は指定できない
@app.delete("/notes/{note_id}", status_code=204, response_model=SomeModel)
def delete_note(note_id: int) -> None: ...

# ✅ response_model を省略する
@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int) -> None: ...
```
