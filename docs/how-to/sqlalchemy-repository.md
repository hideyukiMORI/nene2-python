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
Use a private static method to centralise the cast and keep each query method lean.

```python
from .entity import Book
from .repository import BookRepositoryInterface

class SqlAlchemyBookRepository(BookRepositoryInterface):
    def __init__(self, executor: DatabaseQueryExecutorInterface) -> None:
        self._executor = executor

    @staticmethod
    def _to_book(row: dict[str, object]) -> Book:
        return Book(
            id=int(row["id"]),              # type: ignore[arg-type]
            title=str(row["title"]),
            author=str(row["author"]),
            isbn=str(row["isbn"]),
            published_year=int(row["published_year"]),  # type: ignore[arg-type]
        )
```

> `# type: ignore[arg-type]` is acceptable here: SQLAlchemy returns column values as
> `int | str | float | None | …` depending on the driver, so the cast is correct
> but the static type is `object`. Centralising casts in `_to_entity()` keeps
> `type: ignore` in one place and out of every query method.

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
        return int(row["cnt"]) if row else 0  # type: ignore[arg-type]

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
    def _to_book(row: dict[str, object]) -> Book:
        return Book(
            id=int(row["id"]),              # type: ignore[arg-type]
            title=str(row["title"]),
            author=str(row["author"]),
            isbn=str(row["isbn"]),
            published_year=int(row["published_year"]),  # type: ignore[arg-type]
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

## 4. Use `InMemoryXxxRepository` in tests

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

## 5. Atomic multi-write operations with `transactional()`

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
