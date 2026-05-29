# How-to: レスポンスパターン

FastAPI + nene2 でのレスポンス返却パターンをまとめる。

**既定は「レスポンスモデルのインスタンスを返す」**（§1）。`JSONResponse` を手で返すのは
カスタム status / ヘッダー / ストリーミング / 成功とエラーの混在など特別な場合に限る（§3 以降）。
リファレンス実装 `src/example/*/handler.py` はすべて前者に統一されている。

---

## 1. 既定パターン: レスポンスモデルのインスタンスを返す

ハンドラーは `response_model` を指定し、**その型のインスタンスを返す**。FastAPI が内容を
検証し、宣言したスキーマどおりに直列化する（OpenAPI とレスポンス本体が一致する）。

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class NoteResponse(BaseModel):
    note_id: int = Field(description="ノート ID")
    title: str = Field(description="タイトル")


# ✅ 既定: モデルインスタンスを返す → FastAPI が検証 + 直列化
@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int) -> NoteResponse:
    return NoteResponse(note_id=note_id, title="Hello")
```

> ⚠️ `response_model` を指定しても **`JSONResponse` を直接返すと内容は検証されない**
> （`response_model` は OpenAPI スキーマ生成にのみ使われ、本体はそのまま送られる）。
> 通常ルートでは検証を効かせるためモデルインスタンスを返すこと。`JSONResponse` は
> §3 以降の特別な用途に限る。CLAUDE.md も「`response_model` 明示・`Any` 返却禁止」を定める。

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

変換はハンドラーで明示的に行い、**モデルインスタンスを返す**（§1 の既定パターン）:

```python
@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int) -> NoteResponse:
    note = get_use_case.execute(GetNoteInput(note_id))
    return NoteResponse(note_id=note.note_id, title=note.title)
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
