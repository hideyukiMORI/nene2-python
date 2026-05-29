# 添加新领域

按照与 Note、Tag、Comment 相同的模式添加新领域的检查清单。

## 检查清单

### 1. 创建领域包

```bash
mkdir -p src/example/<domain>
touch src/example/<domain>/__init__.py
```

### 2. 创建各文件

| 文件 | 内容 |
|---|---|
| `entity.py` | 使用 `@dataclass(frozen=True, slots=True)` 定义实体 |
| `repository.py` | `XxxRepositoryInterface(ABC)` + `InMemoryXxxRepository` |
| `exceptions.py` | `XxxNotFoundException` + `XxxNotFoundExceptionHandler` |
| `use_case.py` | 5 个 UseCase（List / Get / Create / Update / Delete）+ Input/Output DTO |
| `handler.py` | `make_xxx_router()` — 解析 → UseCase → 响应 |
| `sqlalchemy_repository.py` | SQL 后端实现 |

### 3. 将表添加到 schema.py

在 `src/example/schema.py` 的 `ensure_schema()` 中添加 `CREATE TABLE` 调用。

```python
executor.write(
    "CREATE TABLE IF NOT EXISTS your_domain ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "name TEXT NOT NULL,"
    "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
    ")"
)
```

### 4. 接入 app.py

更新 `src/example/app.py` 中的 `_build_repositories()` 和 `create_app()`。

```python
# 添加到 _build_repositories() 的返回元组中
your_repo = SqlAlchemyYourRepository(executor)

# 在 create_app() 中注册 router
app.include_router(make_your_router(
    list_use_case=ListYourUseCase(your_repo),
    ...
))
```

### 5. 编写测试

```
tests/example/<domain>/
  __init__.py
  test_<domain>_use_case.py     # UseCase 单元测试（不涉及数据库）
  test_<domain>_repository.py   # Repository 契约测试（InMemory + SQLAlchemy）
  test_<domain>_http.py         # HTTP 集成测试（TestClient）
```

### 6. 注册 MCP 工具（可选）

在 `src/example/mcp.py` 的 `create_mcp_server()` 中添加 UseCase 注册。

### 7. 通过所有检查

```bash
uv run pytest && \
uv run mypy src/ && \
uv run ruff check src/ tests/ && \
uv run ruff format --check src/ tests/
```

## 命名规范

| 目标 | 规范 | 示例 |
|---|---|---|
| 实体类 | PascalCase | `Note`、`Tag`、`Comment` |
| UseCase 输入 DTO | `XxxInput` | `CreateNoteInput` |
| 异常 | `XxxNotFoundException` | `NoteNotFoundException` |
| Handler 工厂 | `make_xxx_router()` | `make_note_router()` |

## 参考实现

- `src/example/note/` — 基础 CRUD 领域
- `src/example/comment/` — 含外键（`note_id`）的嵌套领域
