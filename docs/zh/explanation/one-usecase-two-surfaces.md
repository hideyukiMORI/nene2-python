# 一个 UseCase，两个接入面（HTTP + MCP）

NENE2 的核心承诺是**"LLM 交付就绪"**：同一领域逻辑既作为应用程序的 JSON HTTP API 交付，也作为 LLM 智能体的 [MCP](https://modelcontextprotocol.io/) 工具交付 — 只写一次，无需为每个接入面重复实现。本页以参考应用为例，展示具体做法。

## 共享核心

领域逻辑位于 **UseCase** 类中，对 FastAPI 和 SQLAlchemy 一无所知（[`src/example/note/use_case.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/note/use_case.py)）。两个接入面构造*相同的* UseCase 并调用 `.execute()`：

**HTTP** — [`src/example/note/handler.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/note/handler.py)：

```python
@router.post("", status_code=201, response_model=NoteResponse, summary="Create a note")
async def create_note(body: CreateNoteBody) -> NoteResponse:
    note = create_use_case.execute(CreateNoteInput(body.title, body.body))
    return NoteResponse(id=note.id, title=note.title, body=note.body)
```

handler 是纯粹的*解析 → UseCase → 响应*：不包含任何领域规则。长度和非空校验位于 `CreateNoteInput`（见下文），因此无论哪个接入面调用，规则都会生效。

**MCP** — [`src/example/mcp.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/mcp.py)：

```python
@server.tool("Create a new note.")
def create_note(title: str, body: str) -> dict:
    return asdict(note_create.execute(CreateNoteInput(title=title, body=body)))
```

同一个 `CreateNoteUseCase`，同一个 `CreateNoteInput`，同一个 repository — 只有**边缘**不同。UseCase 的 `Input`/`Output` DTO 就是两个接入面的契约；FastMCP 从函数签名推导工具 schema，FastAPI 从 Pydantic body 和 `response_model` 推导 OpenAPI schema。

## 这带来什么收益

- 领域只需**编写和测试一次**；从同一代码路径同时交付给应用（HTTP）和智能体（MCP）。
- UseCase 中修复的 bug 会**同时**修复两个接入面。
- 新领域只要 UseCase 存在，就立刻可被智能体访问 — `mcp.py` 以零额外配置连接 15 个工具（Note / Tag / Comment）。

## 证明（测试，而非断言）

[`tests/example/test_http_mcp_parity.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/tests/example/test_http_mcp_parity.py) 将 HTTP 应用和 MCP 服务器接入**同一个** SQLite 存储，并断言两个接入面可互换：

- 通过 MCP `create_note` 工具创建的笔记，可以通过 `GET /examples/notes/{id}` 读取；
- 通过 HTTP `POST /examples/notes` 创建的笔记，可以通过 MCP `get_note` 工具读取；
- 两次写入落在同一个存储中。

这将差异化能力作为回归测试加以保护 — 如果两个接入面发生偏离，CI 会失败。

## 什么是共享的，什么不是

划分边界在于**领域规则 vs. 传输机制**。笔记无论以何种方式到达都必须成立的内容，位于 UseCase 的 Input DTO 中，因此两个接入面都会执行；协议配置留在边缘。

| 关注点 | 所在位置 | 与 MCP 共享？ |
|---|---|---|
| 长度限制（`max_length`）、非空校验 | `use_case.py` 中 `CreateNoteInput.__post_init__` | **是** |
| 创建/读取/更新/删除逻辑、不存在语义 | UseCase + 实体 | **是** |
| 请求解析、参数形状/类型 | Pydantic body（HTTP）/ FastMCP 签名（MCP） | 各接入面独有 |
| 身份验证、CORS、限流 | `app.py` 中的 middleware | 否 |
| 分页解析、RFC 9457 错误格式化 | HTTP 层 | 否 |

HTTP 的 `CreateNoteBody` 通过同一个 `MAX_NOTE_TITLE_LENGTH` 常量镜像 `max_length` — 限制只声明一次，在 OpenAPI 中有文档，*并且*在领域中对 MCP 路径执行。

这正是**API 优先 / 薄 HTTP 层**原则的体现：边缘适配各自的协议，中心保持领域不变。对实现者而言，实用规则是：

> 如果规则必须对**两个**接入面成立，将其放在 UseCase 或实体中 — 而非 handler。只在 HTTP handler 中的校验**不能**保护 MCP 工具。（这正是长度和非空校验被移入 Input DTO 的原因 — 参见一致性测试。）

## 参阅

- [设计哲学 → LLM 交付就绪](design-philosophy.md)
- [架构概览](architecture.md)
- [ADR 0011 — MCP 作为核心依赖](../adr/0011-mcp-as-core-dependency.md)
- [如何设置 MCP 服务器](../howto/mcp-setup.md)
