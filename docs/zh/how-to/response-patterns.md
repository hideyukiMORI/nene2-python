# 操作指南：响应模式

使用 FastAPI + nene2 返回响应的模式。

**默认模式是"返回响应模型的实例"**（§1）。仅在特殊情况下才手动返回 `JSONResponse` — 如自定义状态码/头部/流式响应/混合成功与错误（§3 起）。参考实现 `src/example/*/handler.py` 统一使用前者。

---

## 1. 默认模式：返回响应模型实例

handler 声明 `response_model` 并**返回该类型的实例**。FastAPI 验证内容并按声明的 schema 序列化（确保 OpenAPI 和响应体一致）。

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class NoteResponse(BaseModel):
    note_id: int = Field(description="Note ID")
    title: str = Field(description="Title")


# ✅ 默认：返回模型实例 → FastAPI 验证 + 序列化
@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int) -> NoteResponse:
    return NoteResponse(note_id=note_id, title="Hello")
```

> 即使设置了 `response_model`，**直接返回 `JSONResponse` 也会跳过其内容的验证**（`response_model` 仅用于 OpenAPI schema 生成，响应体原样发送）。对于普通路由，返回模型实例以确保验证生效。仅在 §3 起的特殊情况使用 `JSONResponse`。CLAUDE.md 同样要求"声明 `response_model`；禁止返回 `Any`"。

---

## 2. 领域 dataclass vs. Pydantic 响应模型：两个定义

在 nene2 中，领域层和 HTTP 层是分离的，因此会出现两个包含相同字段的类。

```python
# 领域层：frozen dataclass（数据库返回值、UseCase I/O）
@dataclass(frozen=True, slots=True)
class Note:
    note_id: int
    title: str

# HTTP 层：Pydantic 模型（OpenAPI schema 生成、验证）
class NoteResponse(BaseModel):
    note_id: int = Field(description="Note ID")
    title: str = Field(description="Title")
```

**为何需要两个？** `dataclass` 是表达领域不变量的值对象；Pydantic `BaseModel` 是 HTTP 边界的序列化/schema 定义，两者职责不同。

在 handler 中显式转换，并**返回模型实例**（§1 的默认模式）：

```python
@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int) -> NoteResponse:
    note = get_use_case.execute(GetNoteInput(note_id))
    return NoteResponse(note_id=note.note_id, title=note.title)
```

---

## 3. 混合使用 problem_details_response() 和 JSONResponse

当同一 endpoint 在成功时返回 `JSONResponse`，在错误时返回 `problem_details_response()` 时，两者的返回类型不同。由于两者都是 `JSONResponse` 的实例或子类，可以统一返回类型为 `JSONResponse`。

```python
@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int) -> JSONResponse:
    if note_id not in _notes:
        return problem_details_response("not-found", "Not Found", 404, "Note not found.")
    return JSONResponse({"note_id": note_id, "title": "Hello"})
```

---

## 4. `response: Response` 参数与 JSONResponse 不兼容

通过 FastAPI 的 `response: Response` 参数添加头部，并直接返回 `JSONResponse`，**两者无法混用**。

```python
# ❌ 通过 response: Response 设置的头部不会反映在 JSONResponse 中
@app.get("/items/{item_id}")
def get_item(item_id: int, response: Response) -> JSONResponse:
    response.headers["X-Custom"] = "value"  # 无效
    return JSONResponse({"item_id": item_id})

# ✅ 直接将头部传给 JSONResponse
@app.get("/items/{item_id}")
def get_item(item_id: int) -> JSONResponse:
    return JSONResponse({"item_id": item_id}, headers={"X-Custom": "value"})
```

`response: Response` 参数仅在 FastAPI 自动生成响应对象时有效（即返回 `dict` 时）。

---

## 5. 将 model_dump() 传给 JSONResponse 时需传入 `mode="json"`

将 `model_dump()` 直接传给 `JSONResponse` 时，`datetime` 等 Python 对象无法被 `json.dumps` 序列化，会导致 500 错误。指定 `mode="json"` 使 Pydantic 将其转换为 JSON 兼容类型。

```python
from pydantic import BaseModel
from datetime import datetime

class OrderLine(BaseModel):
    created_at: datetime
    quantity: int

line = OrderLine(created_at=datetime(2026, 1, 1), quantity=3)

# ❌ TypeError：datetime 类型无法序列化为 JSON
return JSONResponse(line.model_dump())

# ✅ mode="json" 将 datetime 转换为 ISO 8601 字符串
return JSONResponse(line.model_dump(mode="json"))
```

**常见陷阱**：使用 `response_model=` 的普通路由不受影响，因为 FastAPI 会自动转换。注意直接返回 `JSONResponse` 的路由（207 Multi-Status、自定义响应、包含嵌套模型的 `/preview` 等）。

---

## 6. 204 No Content 与 response_model

在 `204 No Content` 的 endpoint 上指定 `response_model` 会导致 FastAPI 断言错误。

```python
# ❌ 204 上不能指定 response_model
@app.delete("/notes/{note_id}", status_code=204, response_model=SomeModel)
def delete_note(note_id: int) -> None: ...

# ✅ 省略 response_model
@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int) -> None: ...
```
