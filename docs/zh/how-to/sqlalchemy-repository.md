# 实现 SQLAlchemy Repository

本指南展示如何使用 `SqlAlchemyQueryExecutor` 编写 `SqlAlchemyXxxRepository`，实现原生 SQL 持久化 — 无 ORM，无魔法。

## 前提条件

- 已有领域脚手架（`entity.py`、`repository.py`、`use_case.py`、`handler.py`）
- 运行中的 nene2 应用，使用 `AppSettings` 且 `DB_ADAPTER=sqlite`（或 `mysql` / `pgsql`）

---

## 1. 创建 `sqlalchemy_repository.py`

### schema 辅助函数

在文件顶部定义 `ensure_schema()`，在 `create_app()` 中调用一次。

```python
from nene2.database import DatabaseQueryExecutorInterface

def ensure_schema(executor: DatabaseQueryExecutorInterface) -> None:
    executor.write(
        """
        CREATE TABLE IF NOT EXISTS books (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            title          TEXT    NOT NULL,
            author         TEXT    NOT NULL,
            isbn           TEXT    NOT NULL,
            published_year INTEGER NOT NULL
        )
        """
    )
```

> 将 `ensure_schema()` 放在 `sqlalchemy_repository.py` 中（而非单独的 `schema.py`），使 schema 定义与拥有该表的 repository 在一起。对于有共享 schema 文件的多领域应用，每个领域保留一个 `ensure_schema()`，并在 `create_app()` 中逐一调用。

### 行到实体的转换辅助方法

`fetch_one` / `fetch_all` 返回 `dict[str, Any]`。使用私有静态方法集中映射逻辑，保持各查询方法简洁。

```python
from typing import Any
from .entity import Book
from .repository import BookRepositoryInterface

class SqlAlchemyBookRepository(BookRepositoryInterface):
    def __init__(self, executor: DatabaseQueryExecutorInterface) -> None:
        self._executor = executor

    @staticmethod
    def _to_book(row: dict[str, Any]) -> Book:
        return Book(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            isbn=row["isbn"],
            published_year=row["published_year"],
        )
```

> 使用 `dict[str, Any]` 而非 `dict[str, object]`。`fetch_one()` / `fetch_all()` 返回 `dict[str, Any]`，`row["id"]` 类型为 `Any`，在 `mypy --strict` 下可直接赋值给 `int` 而无需强制转换。使用 `dict[str, object]` 则需要 `# type: ignore[call-overload]` 并会触发后续的 `unused-ignore` 错误。

### 完整实现

```python
class SqlAlchemyBookRepository(BookRepositoryInterface):
    def __init__(self, executor: DatabaseQueryExecutorInterface) -> None:
        self._executor = executor

    def find_all(self, limit: int, offset: int) -> list[Book]:
        rows = self._executor.fetch_all(
            "SELECT id, title, author, isbn, published_year FROM books "
            "ORDER BY id LIMIT :limit OFFSET :offset",
            {"limit": limit, "offset": offset},
        )
        return [self._to_book(row) for row in rows]

    def count_all(self) -> int:
        row = self._executor.fetch_one("SELECT COUNT(*) AS cnt FROM books")
        return int(row["cnt"]) if row else 0

    def find_by_id(self, book_id: int) -> Book | None:
        row = self._executor.fetch_one(
            "SELECT id, title, author, isbn, published_year FROM books WHERE id = :id",
            {"id": book_id},
        )
        return self._to_book(row) if row else None

    def save(self, book: Book) -> Book:
        new_id = self._executor.write(
            "INSERT INTO books (title, author, isbn, published_year) "
            "VALUES (:title, :author, :isbn, :published_year)",
            {"title": book.title, "author": book.author,
             "isbn": book.isbn, "published_year": book.published_year},
        )
        return Book(id=new_id, title=book.title, author=book.author,
                    isbn=book.isbn, published_year=book.published_year)

    def update(self, book: Book) -> Book:
        self._executor.write(
            "UPDATE books SET title=:title, author=:author, isbn=:isbn, "
            "published_year=:published_year WHERE id=:id",
            {"title": book.title, "author": book.author,
             "isbn": book.isbn, "published_year": book.published_year, "id": book.id},
        )
        return book

    def delete(self, book_id: int) -> None:
        self._executor.write("DELETE FROM books WHERE id = :id", {"id": book_id})

    @staticmethod
    def _to_book(row: dict[str, Any]) -> Book:
        return Book(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            isbn=row["isbn"],
            published_year=row["published_year"],
        )
```

---

## 2. 接入 `create_app()`

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from nene2.config import AppSettings
from nene2.database import SqlAlchemyQueryExecutor

from bookshelf.repository import BookRepositoryInterface, InMemoryBookRepository
from bookshelf.sqlalchemy_repository import SqlAlchemyBookRepository, ensure_schema


def _build_repository(cfg: AppSettings) -> BookRepositoryInterface:
    if cfg.db_adapter == "sqlite":
        is_memory = cfg.db_name == ":memory:"
        engine = create_engine(
            cfg.db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if is_memory else None,
        )
        executor = SqlAlchemyQueryExecutor(engine)
        ensure_schema(executor)          # 首次运行时创建表
        return SqlAlchemyBookRepository(executor)
    return InMemoryBookRepository()      # 测试/本地开发时的回退
```

> 将 if/else 分支封装在返回接口类型的辅助函数（如 `_build_repository()`）中。这比在 `create_app()` 中先声明 `repo: BookRepositoryInterface` 再 if/else 更清晰 — 两种方式都满足 `mypy --strict`，但辅助函数让 `create_app()` 更易读。

> 内存 SQLite（`DB_NAME=:memory:`）必须使用 `StaticPool`，防止 SQLAlchemy 打开多个连接（每个连接都会看到空数据库）。基于文件的 SQLite 和其他适配器不需要。

---

## 3. `write()` 的返回值

`executor.write()` 返回：

| 操作 | 返回值 |
|---|---|
| `INSERT` | `lastrowid` — 新行自动生成的整型主键 |
| `UPDATE` / `DELETE` | `rowcount` — 受影响的行数（未匹配时为 0） |

使用 `lastrowid` 在 INSERT 后重建实体：

```python
new_id = self._executor.write("INSERT INTO ...", {...})
return Book(id=new_id, ...)
```

使用 `rowcount` 检测 UPDATE / DELETE 时的缺失行：

```python
affected = self._executor.write("UPDATE books SET ... WHERE id = :id", {"id": book_id})
if affected == 0:
    raise BookNotFoundException(book_id)
```

> 对于 SQLite、MySQL、PostgreSQL 上的单行 INSERT，`lastrowid` 保证是正整数。多行 INSERT 或无 `AUTOINCREMENT` / `SERIAL` 列时为 `0` — 如需取回 ID，避免这些情况。

---

## 4. 包含 `datetime` 字段的实体

当实体有 `created_at: datetime` 字段，由数据库通过 `DEFAULT CURRENT_TIMESTAMP` 生成时，使用 `nene2.database` 中的 `parse_db_datetime()`。

### 为何需要它

SQLite 将 `CURRENT_TIMESTAMP` 存储为**纯字符串**（`"2026-05-20 12:34:56"`），而非 Python `datetime` 对象。`datetime.fromisoformat()` 可以解析字符串，但返回**朴素** datetime（无时区），导致 JSON 响应泄露模糊时间戳。`parse_db_datetime()` 透明地处理三种情况：

| 驱动 | 原始值 | `parse_db_datetime()` 后 |
|---|---|---|
| SQLite | `"2026-05-20 12:34:56"`（str） | `datetime(…, tzinfo=UTC)` |
| MySQL/PostgreSQL | 朴素 `datetime` 对象 | `datetime(…, tzinfo=UTC)` |
| MySQL/PostgreSQL | 有时区 `datetime` 对象 | 不变 |

### Schema

```python
"created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
```

### INSERT 后查询模式

`write()` 只返回 `lastrowid`，不返回数据库生成的 `created_at`。使用第二次 `fetch_one()` 获取完整行：

```python
from datetime import datetime
from typing import Any

from nene2.database import DatabaseQueryExecutorInterface, parse_db_datetime

from .entity import Post

def _to_post(row: dict[str, Any]) -> Post:
    return Post(
        id=row["id"],
        title=row["title"],
        body=row["body"],
        created_at=parse_db_datetime(row["created_at"]),
    )

class SqlAlchemyPostRepository(PostRepositoryInterface):
    def save(self, title: str, body: str) -> Post:
        new_id = self._executor.write(
            "INSERT INTO posts (title, body) VALUES (:title, :body)",
            {"title": title, "body": body},
        )
        row = self._executor.fetch_one(
            "SELECT id, title, body, created_at FROM posts WHERE id = :id",
            {"id": new_id},
        )
        if row is None:
            raise RuntimeError(f"Row {new_id} not found after INSERT into posts")
        return _to_post(row)
```

> `if row is None: raise RuntimeError(...)` 保护是必要的，因为 `fetch_one()` 返回 `dict | None`。INSERT 后的行实际上不可能为 `None` — 这个保护是为了满足类型检查器。优先使用 `RuntimeError` 而非 `assert`：`assert` 在 `python -O` 下会被剥离，并被 ruff 的 S101 规则在非测试代码中标记。

### InMemory repository 中的 datetime

`InMemoryXxxRepository` 应在 Python 中生成时间戳：

```python
from datetime import datetime, timezone

def save(self, title: str, body: str) -> Post:
    now = datetime.now(timezone.utc)
    post = Post(id=self._next_id, title=title, body=body, created_at=now)
    self._store[self._next_id] = post
    self._next_id += 1
    return post
```

### JSON 序列化

对带 UTC 时区的 datetime 调用 `isoformat()` 产生 `"2026-05-20T12:34:56+00:00"`。在响应字典中以字符串形式返回：

```python
def _post_dict(post: Post) -> dict[str, object]:
    return {
        "id": post.id,
        "title": post.title,
        "body": post.body,
        "created_at": post.created_at.isoformat(),   # "2026-05-20T12:34:56+00:00"
    }
```

---

## 5. 嵌套资源 — DELETE 中的归属验证

当资源嵌套在父资源下（如 `DELETE /posts/{post_id}/comments/{comment_id}`）时，始终在 UseCase 中验证子资源属于父资源，而非仅在数据库层面验证。

### 错误 — 忽略 `post_id`

```python
# handler
@router.delete("/posts/{post_id}/comments/{comment_id}", status_code=204)
async def delete_comment(post_id: int, comment_id: int) -> None:
    delete_use_case.execute(DeleteCommentInput(comment_id))  # post_id 未使用！
```

这允许 `DELETE /posts/1/comments/5` 删除属于 post 2 的 comment 5。

### 正确 — 在 UseCase 中验证归属

```python
# use_case.py
@dataclass(frozen=True, slots=True)
class DeleteCommentInput:
    post_id: int
    comment_id: int

class DeleteCommentUseCase:
    def execute(self, input_: DeleteCommentInput) -> None:
        comment = self._repository.find_by_id(input_.comment_id)
        if comment is None or comment.post_id != input_.post_id:
            raise CommentNotFoundException(input_.comment_id)
        self._repository.delete(input_.comment_id)

# handler
@router.delete("/posts/{post_id}/comments/{comment_id}", status_code=204)
async def delete_comment(post_id: int, comment_id: int) -> None:
    delete_use_case.execute(DeleteCommentInput(post_id, comment_id))
```

> 同样的模式适用于嵌套资源的 GET 和 PUT：始终将 `post_id` 传入 UseCase 并验证 `comment.post_id == input_.post_id`。

---

## 6. 在测试中使用 `InMemoryXxxRepository`

永远不要模拟（mock）数据库，单元测试使用内存实现：

```python
from bookshelf.repository import InMemoryBookRepository
from bookshelf.use_case import CreateBookUseCase, CreateBookInput

def test_create_book() -> None:
    repo = InMemoryBookRepository()
    use_case = CreateBookUseCase(repo)
    book = use_case.execute(CreateBookInput(
        title="Clean Code", author="Robert C. Martin",
        isbn="978-0132350884", published_year=2008,
    ))
    assert book.id == 1
    assert book.title == "Clean Code"
```

SQLAlchemy repository 测试使用内存 SQLite 引擎：

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from nene2.database import SqlAlchemyQueryExecutor
from bookshelf.sqlalchemy_repository import SqlAlchemyBookRepository, ensure_schema

def _make_repo() -> SqlAlchemyBookRepository:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    executor = SqlAlchemyQueryExecutor(engine)
    ensure_schema(executor)
    return SqlAlchemyBookRepository(executor)
```

---

## 7. 使用 `transactional()` 进行原子多写操作

当 UseCase 需要原子地写入多张表时，结合使用 `SqlAlchemyTransactionManager.transactional()` 和 repository 的 `_in_tx` 方法。

### 在接口上定义 `_in_tx` 方法

添加接受显式 `executor` 参数的专用方法，这些方法仅在 `transactional()` 回调内调用，绝不在外部调用。

```python
from nene2.database import DatabaseQueryExecutorInterface
from abc import ABC, abstractmethod

class AccountRepositoryInterface(ABC):
    @abstractmethod
    def find_by_id(self, account_id: int) -> Account | None: ...

    # _in_tx 变体 — executor 由 transactional() 回调提供
    @abstractmethod
    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None: ...

    @abstractmethod
    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta_cents: int
    ) -> None: ...
```

### 在 SQLAlchemy repository 中实现 `_in_tx` 方法

`_in_tx` 方法使用传入的 `executor` 而非 `self._executor`，从而共享同一连接并参与同一事务。

```python
class SqlAlchemyAccountRepository(AccountRepositoryInterface):
    def __init__(self, executor: SqlAlchemyQueryExecutor) -> None:
        self._executor = executor

    def find_by_id(self, account_id: int) -> Account | None:
        row = self._executor.fetch_one(
            "SELECT id, name, balance_cents FROM accounts WHERE id = :id",
            {"id": account_id},
        )
        return self._to_entity(row) if row else None

    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None:
        row = executor.fetch_one(
            "SELECT id, name, balance_cents FROM accounts WHERE id = :id",
            {"id": account_id},
        )
        return self._to_entity(row) if row else None

    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta_cents: int
    ) -> None:
        executor.write(
            "UPDATE accounts SET balance_cents = balance_cents + :delta WHERE id = :id",
            {"delta": delta_cents, "id": account_id},
        )
```

### 使用 `SqlAlchemyTransactionManager` 组装 UseCase

```python
from nene2.database import SqlAlchemyTransactionManager

engine = create_engine(cfg.db_url, connect_args={"check_same_thread": False})
transaction_manager = SqlAlchemyTransactionManager(engine)

transfer_use_case = TransferUseCase(transaction_manager, account_repo, transfer_repo)
```

### 为单元测试实现 InMemory `_in_tx`

InMemory 实现忽略 executor — 操作直接对内存存储进行。`InMemoryTransactionManager` 使用无操作 executor 立即调用回调。

```python
from nene2.database import DatabaseQueryExecutorInterface, DatabaseTransactionManagerInterface
from collections.abc import Callable

class InMemoryAccountRepository(AccountRepositoryInterface):
    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None:
        return self._accounts.get(account_id)

    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta_cents: int
    ) -> None:
        account = self._accounts[account_id]
        self._accounts[account_id] = Account(
            id=account.id, name=account.name, balance_cents=account.balance_cents + delta_cents
        )

class _NoOpExecutor(DatabaseQueryExecutorInterface):
    def fetch_all(self, sql: str, params: dict[str, object] | None = None) -> list[dict[str, object]]:
        return []
    def fetch_one(self, sql: str, params: dict[str, object] | None = None) -> dict[str, object] | None:
        return None
    def write(self, sql: str, params: dict[str, object] | None = None) -> int:
        return 0

class InMemoryTransactionManager(DatabaseTransactionManagerInterface):
    def transactional[T](self, callback: Callable[[DatabaseQueryExecutorInterface], T]) -> T:
        return callback(_NoOpExecutor())
    def begin(self) -> None: pass
    def commit(self) -> None: pass
    def rollback(self) -> None: pass
```

> **发生异常时回滚**：`SqlAlchemyTransactionManager.transactional()` 使用 `engine.begin()` — 回调内的任何异常都会触发自动回滚。领域异常（`AccountNotFoundException` 等）在回滚后正常传播。

---

## 6. 使用 MySQL 8

### 所需包

MySQL 8 默认使用 `caching_sha2_password` 认证。同时安装 `pymysql` 和 `cryptography` — 缺少 `cryptography` 会导致连接失败，报错 `Authentication plugin 'caching_sha2_password' is not supported`。

```bash
uv add pymysql cryptography
```

### 连接 URL

```python
url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
engine = create_engine(url, pool_pre_ping=True)
```

推荐 MySQL 使用 `pool_pre_ping=True` — 在使用前测试连接，处理服务器 `wait_timeout` 后的陈旧连接。

### 健康检查

`DatabaseHealthCheck` 接受 **`SqlAlchemyQueryExecutor`**，而非直接接受引擎：

```python
from nene2.database import DatabaseHealthCheck, SqlAlchemyQueryExecutor

executor = SqlAlchemyQueryExecutor(engine)
health = DatabaseHealthCheck(executor)   # ← executor，不是 engine

app.add_api_route("/health", health.check, methods=["GET"])
```

### `CURRENT_TIMESTAMP` 类型差异

SQLite 将 `CURRENT_TIMESTAMP` 返回为 `str`；MySQL 返回朴素 `datetime` 对象。在 `_to_entity()` 中使用 `parse_db_datetime()` 透明地处理两者：

```python
from nene2.database import parse_db_datetime

def _to_entity(row: dict[str, Any]) -> Product:
    return Product(
        id=int(row["id"]),
        created_at=parse_db_datetime(row["created_at"]),  # 同时适用于 SQLite 和 MySQL
    )
```

### Docker Compose 示例

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: mydb
      MYSQL_USER: appuser
      MYSQL_PASSWORD: apppass
    ports:
      - "3310:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-uappuser", "-papppass"]
      interval: 5s
      timeout: 5s
      retries: 10

  app:
    build: .
    depends_on:
      mysql:
        condition: service_healthy
```
