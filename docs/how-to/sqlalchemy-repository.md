# Implement a SQLAlchemy repository

This guide shows how to write a `SqlAlchemyXxxRepository` that uses
`SqlAlchemyQueryExecutor` for raw-SQL persistence — no ORM, no magic.

## Prerequisites

- A domain already scaffolded (`entity.py`, `repository.py`, `use_case.py`, `handler.py`)
- A running nene2 app using `AppSettings` with `DB_ADAPTER=sqlite` (or `mysql` / `pgsql`)

---

## 1. Create `sqlalchemy_repository.py`

### Schema helper

Define `ensure_schema()` at the top of the file.
Call it once at startup from `create_app()`.

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

> Put `ensure_schema()` in `sqlalchemy_repository.py` (not a separate `schema.py`),
> so the schema definition lives next to the repository that owns the table.
> For multi-domain apps with a shared schema file, keep one `ensure_schema()` per domain
> and call them all from `create_app()`.

### Row-to-entity helper

`fetch_one` / `fetch_all` return `dict[str, Any]`.
Use a private static method to centralise the mapping and keep each query method lean.

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

> Use `dict[str, Any]` — not `dict[str, object]`.
> `fetch_one()` / `fetch_all()` return `dict[str, Any]`, so `row["id"]` is `Any`
> which is assignable to `int` under `mypy --strict` without any casts.
> Using `dict[str, object]` instead requires `# type: ignore[call-overload]`
> and triggers follow-up `unused-ignore` errors.

### Full implementation

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

## 2. Wire into `create_app()`

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
        ensure_schema(executor)          # creates table on first run
        return SqlAlchemyBookRepository(executor)
    return InMemoryBookRepository()      # fallback for tests / local dev
```

> Wrap the if/else branch in a helper function like `_build_repository()` that
> returns the interface type. This is cleaner than declaring `repo: BookRepositoryInterface`
> before an if/else block in `create_app()` — both approaches satisfy `mypy --strict`,
> but the helper keeps `create_app()` readable.
>
> If you prefer inline branching, declare the type first:
> ```python
> repo: BookRepositoryInterface
> if cfg.db_adapter == "sqlite":
>     repo = SqlAlchemyBookRepository(executor)
> else:
>     repo = InMemoryBookRepository()
> ```

> `StaticPool` is required for SQLite in-memory databases (`DB_NAME=:memory:`) to prevent
> SQLAlchemy from opening multiple connections — each of which would see an empty database.
> File-based SQLite and other adapters do not need it.

---

## 3. `write()` return value

`executor.write()` returns:

| Operation | Return value |
|---|---|
| `INSERT` | `lastrowid` — the auto-generated integer primary key of the new row |
| `UPDATE` / `DELETE` | `rowcount` — number of rows affected (0 if nothing matched) |

Use `lastrowid` to reconstruct the entity after INSERT:

```python
new_id = self._executor.write("INSERT INTO ...", {...})
return Book(id=new_id, ...)
```

Use `rowcount` to detect missing rows on UPDATE / DELETE:

```python
affected = self._executor.write("UPDATE books SET ... WHERE id = :id", {"id": book_id})
if affected == 0:
    raise BookNotFoundException(book_id)
```

> `lastrowid` is guaranteed to be a positive `int` for single-row INSERTs on SQLite,
> MySQL, and PostgreSQL. It is `0` for multi-row INSERTs or when the table has no
> `AUTOINCREMENT` / `SERIAL` column — avoid those patterns if you need the ID back.

---

## 4. Entities with `datetime` fields

When your entity has a `created_at: datetime` field backed by a database-generated
`DEFAULT CURRENT_TIMESTAMP`, use `parse_db_datetime()` from `nene2.database`.

### Why it is needed

SQLite stores `CURRENT_TIMESTAMP` as a **plain string** (`"2026-05-20 12:34:56"`),
not as a Python `datetime` object. `datetime.fromisoformat()` parses the string but
returns a **naive** datetime (no timezone), so the JSON response leaks an ambiguous
timestamp. `parse_db_datetime()` handles all three cases transparently:

| Driver | Raw value | After `parse_db_datetime()` |
|---|---|---|
| SQLite | `"2026-05-20 12:34:56"` (str) | `datetime(…, tzinfo=UTC)` |
| MySQL/PostgreSQL | naive `datetime` object | `datetime(…, tzinfo=UTC)` |
| MySQL/PostgreSQL | aware `datetime` object | unchanged |

### Schema

```python
"created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
```

### SELECT-after-INSERT pattern

After `write()` you only get back the `lastrowid`, not the DB-generated `created_at`.
Do a second `fetch_one()` to retrieve the full row:

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

> The `if row is None: raise RuntimeError(...)` guard is needed because `fetch_one()`
> returns `dict | None`. The row cannot actually be `None` right after INSERT — the guard
> exists to satisfy the type checker. Prefer `RuntimeError` over `assert`: `assert`
> is stripped by `python -O` and flagged by ruff's S101 rule in non-test code.

### InMemory repository with datetime

The `InMemoryXxxRepository` should generate the timestamp in Python:

```python
from datetime import datetime, timezone

def save(self, title: str, body: str) -> Post:
    now = datetime.now(timezone.utc)
    post = Post(id=self._next_id, title=title, body=body, created_at=now)
    self._store[self._next_id] = post
    self._next_id += 1
    return post
```

### JSON serialisation

`datetime.isoformat()` on a UTC-aware datetime produces `"2026-05-20T12:34:56+00:00"`.
Return it as a string in the response dict:

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

## 5. Nested resources — ownership validation in DELETE

When a resource is nested under a parent (e.g. `DELETE /posts/{post_id}/comments/{comment_id}`),
always validate that the child belongs to the parent in the UseCase, not just in the database.

### Wrong — ignores `post_id`

```python
# handler
@router.delete("/posts/{post_id}/comments/{comment_id}", status_code=204)
async def delete_comment(post_id: int, comment_id: int) -> None:
    delete_use_case.execute(DeleteCommentInput(comment_id))  # post_id unused!
```

This allows `DELETE /posts/1/comments/5` to delete comment 5 even when it belongs to post 2.

### Correct — validate ownership in the UseCase

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

> The same pattern applies to GET and PUT on nested resources:
> always pass `post_id` into the UseCase and verify `comment.post_id == input_.post_id`.

---

## 6. Use `InMemoryXxxRepository` in tests

Never mock the database. Use the in-memory implementation for unit tests:

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

For SQLAlchemy repository tests, use an in-memory SQLite engine:

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

## 7. Atomic multi-write operations with `transactional()`

When a UseCase needs to write to multiple tables atomically, use `SqlAlchemyTransactionManager.transactional()` together with `_in_tx` repository methods.

### Define `_in_tx` methods on the interface

Add dedicated methods that accept an explicit `executor` parameter. These are called only inside a `transactional()` callback — never outside one.

```python
from nene2.database import DatabaseQueryExecutorInterface
from abc import ABC, abstractmethod

class AccountRepositoryInterface(ABC):
    @abstractmethod
    def find_by_id(self, account_id: int) -> Account | None: ...

    # _in_tx variants — executor is provided by the transactional() callback
    @abstractmethod
    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None: ...

    @abstractmethod
    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta_cents: int
    ) -> None: ...
```

### Implement `_in_tx` methods in the SQLAlchemy repository

The `_in_tx` methods use the passed-in `executor` instead of `self._executor`, so they share the same connection and participate in the same transaction.

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

### Wire the UseCase with `SqlAlchemyTransactionManager`

```python
from nene2.database import SqlAlchemyTransactionManager

engine = create_engine(cfg.db_url, connect_args={"check_same_thread": False})
transaction_manager = SqlAlchemyTransactionManager(engine)

transfer_use_case = TransferUseCase(transaction_manager, account_repo, transfer_repo)
```

### Implement InMemory `_in_tx` for unit tests

The InMemory implementation ignores the executor — operations go directly to the in-memory store. `InMemoryTransactionManager` calls the callback immediately with a no-op executor.

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

> **Rollback on exception**: `SqlAlchemyTransactionManager.transactional()` uses `engine.begin()` — any exception inside the callback triggers an automatic rollback. Domain exceptions (`AccountNotFoundException`, etc.) propagate normally after rollback.
