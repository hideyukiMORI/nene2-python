# 运行测试

## 基本命令

```bash
# 运行所有测试并生成覆盖率报告
uv run pytest

# 失败时显示详细输出
uv run pytest --tb=short -v

# 运行特定目录
uv run pytest tests/example/note/

# 生成 HTML 覆盖率报告
uv run pytest --cov=src --cov-report=html
# → 在浏览器中打开 htmlcov/index.html
```

## 测试结构

```
tests/
  nene2/              框架核心单元测试
    use_case/         UseCaseProtocol 合规性测试
    auth/             Auth middleware 和 verifier 测试
    database/         TransactionManager 测试
    mcp/              McpHttpClient 测试
    middleware/       各 middleware 独立测试
  example/
    note/             Note 领域测试
      test_list_notes.py           UseCase 单元测试
      test_note_repository.py      Repository 契约测试
      test_async_note_use_case.py  异步 UseCase 测试
    comment/
      test_comment_use_case.py     UseCase 单元测试（不涉及数据库）
      test_comment_repository.py   InMemory + SQLAlchemy 契约测试
      test_comment_http.py         HTTP 集成测试（TestClient）
```

## 测试类型

### UseCase 单元测试

无数据库，无 HTTP — 使用 InMemory repository，速度最快。

```python
def test_create_note() -> None:
    repo = InMemoryNoteRepository()
    note = CreateNoteUseCase(repo).execute(CreateNoteInput(title="t", body="b"))
    assert note.title == "t"
```

### Repository 契约测试

`@pytest.fixture(params=["inmemory", "sqlalchemy"])` 对两种实现运行相同的断言。

```python
@pytest.fixture(params=["inmemory", "sqlalchemy"])
def repo(request): ...

def test_save_and_find(repo) -> None:
    note = repo.save("title", "body")
    assert repo.find_by_id(note.id) == note
```

### HTTP 集成测试

使用 FastAPI 的 `TestClient`，测试从 HTTP 到 repository 的完整栈。

```python
def test_create_note_returns_201() -> None:
    client = TestClient(create_app(AppSettings(throttle_enabled=False)))
    response = client.post("/notes", json={"title": "t", "body": "b"})
    assert response.status_code == 201
```

### 异步测试

`pyproject.toml` 中设置了 `asyncio_mode = "auto"`，因此 `async def test_*` 可以直接使用。

```python
async def test_async_list_notes() -> None:
    repo = InMemoryNoteRepository()
    result = await AsyncListNotesUseCase(repo).execute(ListNotesInput(limit=10, offset=0))
    assert result.total == 0
```

## 集成测试使用内存 SQLite

在使用 `SqlAlchemyQueryExecutor` 或 `SqlAlchemyTransactionManager` 配合内存 SQLite 数据库时，请始终传入 `poolclass=StaticPool`。否则 SQLAlchemy 可能打开新的物理连接，看到的是空数据库。

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

`StaticPool` 确保所有逻辑连接共享同一个底层 SQLite 连接，使某次操作创建的表在后续操作中可见。

**SQLite 外键强制执行**：SQLite 默认禁用外键约束。在引擎创建后立即使用 `PRAGMA foreign_keys=ON` 启用：

```python
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("PRAGMA foreign_keys=ON"))
```

使用 `StaticPool` 时，一次调用即可应用于单个共享连接，后续所有操作都会强制执行外键约束。

## 使用 caplog 捕获 structlog 输出

在 `conftest.py` 的模块级调用 `configure_for_testing()`，将 structlog 路由到标准库日志，使 pytest 的 `caplog` fixture 可以捕获它。

```python
# conftest.py
from nene2.log import configure_for_testing
configure_for_testing()
```

然后在测试中对消息字符串进行断言：

```python
def test_handler_logs(caplog: pytest.LogCaptureFixture) -> None:
    client = TestClient(create_app())
    client.post("/api/echo", json={"message": "hello"})
    assert any("processing echo" in r.message for r in caplog.records)
```

**注意**：`caplog.records` 返回标准库的 `LogRecord` 对象。通过 `structlog.contextvars.bind_contextvars()` 绑定的字段（如 `request_id`）不能直接通过 `record.request_id` 访问 — 它们以格式化消息字符串的形式出现。

## TestClient HTTP 方法与 json 参数

`TestClient` 的 `.get()`、`.post()`、`.put()`、`.patch()` 接受 `json=` 参数，但 `.delete()` 不接受（`TypeError`）。DELETE 需要带请求体时使用 `.request()`。

```python
# ✅ GET/POST/PUT/PATCH 支持 json=
r = client.post("/items", json={"name": "Alice"})
r = client.put("/items/1", json={"name": "Bob"})

# ❌ DELETE 不支持 json=
r = client.delete("/items/bulk", json={"ids": [1, 2]})  # TypeError

# ✅ DELETE + 请求体时使用 request()
r = client.request("DELETE", "/items/bulk", json={"ids": [1, 2]})
```

**设计注意事项**：RFC 9110 中不推荐 DELETE 携带请求体（某些服务器可能会忽略）。批量删除的替代方案是 `POST /items/bulk-delete` 模式。

---

## 覆盖率要求

| 范围 | 目标 |
|---|---|
| 整体 | ≥ 80%（CI 通过 `pytest --cov-fail-under=80` 强制执行） |
| UseCase / 领域 | ≥ 90%（CI 对 `example/*/use_case.py`、`entity.py`、`async_use_case.py` 强制执行） |

当前基准：**466 个测试**，整体覆盖率约 93%。

## 静态分析

```bash
uv run mypy src/          # 类型检查（严格模式）
uv run ruff check src/ tests/    # Lint
uv run ruff format --check src/ tests/  # 格式检查
uv run pip-audit --ignore-vuln PYSEC-2025-183  # 依赖扫描（与 CI 一致）
```

CI 在 **Python 3.12 和 3.14** 上运行（参见 `.github/workflows/ci.yml`）。
