# SQLAlchemy リポジトリを実装する

`SqlAlchemyQueryExecutor` を使う `SqlAlchemyXxxRepository` の実装パターンを示します。
ORM は使わず、生 SQL でシンプルに永続化します。

## 前提条件

- ドメインのスキャフォールド（`entity.py`, `repository.py`, `use_case.py`, `handler.py`）が完成している
- `AppSettings` で `DB_ADAPTER=sqlite`（または `mysql` / `pgsql`）が設定されている

---

## 1. `sqlalchemy_repository.py` を作る

### スキーマヘルパー

ファイルの先頭に `ensure_schema()` を定義します。
アプリ起動時に `create_app()` から一度だけ呼びます。

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

> `ensure_schema()` はそのテーブルを所有するリポジトリと同じファイルに置きます。
> ドメインが増えた場合も各ドメインの `sqlalchemy_repository.py` に書き、
> `create_app()` から順番に呼び出します。

### row → エンティティ 変換ヘルパー

`fetch_one()` / `fetch_all()` の返り値は `dict[str, Any]` です。
プライベートな静的メソッドに変換ロジックを集約することで、
各クエリメソッドをシンプルに保てます。

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

> `# type: ignore[arg-type]` は必要最小限です。SQLAlchemy はカラム値を
> `int | str | float | None | …` として返すため、静的型は `object` になります。
> キャストを `_to_entity()` に集約することで、他のメソッドには `type: ignore` が不要になります。

### 完全な実装例

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

## 2. `create_app()` に組み込む

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
        ensure_schema(executor)          # 初回起動時にテーブルを作成
        return SqlAlchemyBookRepository(executor)
    return InMemoryBookRepository()      # テスト・ローカル開発用フォールバック
```

> `StaticPool` は SQLite インメモリ DB（`DB_NAME=:memory:`）で必須です。
> 複数コネクションが開くと各コネクションが別々の空 DB を見てしまうため、
> `StaticPool` で接続を 1 本に固定します。ファイルベース SQLite や他のアダプタには不要です。

---

## 3. `write()` の返り値

| 操作 | 返り値 |
|---|---|
| `INSERT` | `lastrowid` — 新規行の自動採番 ID（`int`） |
| `UPDATE` / `DELETE` | `rowcount` — 影響を受けた行数（0 件なら `0`） |

INSERT 後にエンティティを再構築する場合：

```python
new_id = self._executor.write("INSERT INTO ...", {...})
return Book(id=new_id, ...)
```

UPDATE / DELETE で存在しないリソースを検出する場合：

```python
affected = self._executor.write("UPDATE books SET ... WHERE id = :id", {"id": book_id})
if affected == 0:
    raise BookNotFoundException(book_id)
```

---

## 4. テストでは `InMemoryXxxRepository` を使う

DB のモックは禁止です。UseCase のユニットテストはインメモリ実装を使います。

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

SQLAlchemy リポジトリ自体のテストにはインメモリ SQLite エンジンを使います。

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

## 5. `transactional()` を使った原子的マルチライト

複数テーブルへの書き込みを原子的に行う UseCase では、`SqlAlchemyTransactionManager.transactional()` と `_in_tx` リポジトリメソッドを組み合わせます。

### インターフェースに `_in_tx` メソッドを定義する

`transactional()` コールバック内からのみ呼ぶ専用メソッドを用意し、明示的な `executor` を受け取ります。

```python
from nene2.database import DatabaseQueryExecutorInterface
from abc import ABC, abstractmethod

class AccountRepositoryInterface(ABC):
    @abstractmethod
    def find_by_id(self, account_id: int) -> Account | None: ...

    # _in_tx バリアント — transactional() コールバック内からのみ呼ぶ
    @abstractmethod
    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None: ...

    @abstractmethod
    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta_cents: int
    ) -> None: ...
```

### SQLAlchemy リポジトリで `_in_tx` を実装する

`_in_tx` メソッドは `self._executor` の代わりに渡された `executor` を使うため、同じトランザクションに参加します。

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

### UseCase に `SqlAlchemyTransactionManager` を配線する

```python
from nene2.database import SqlAlchemyTransactionManager

engine = create_engine(cfg.db_url, connect_args={"check_same_thread": False})
transaction_manager = SqlAlchemyTransactionManager(engine)

transfer_use_case = TransferUseCase(transaction_manager, account_repo, transfer_repo)
```

### InMemory 版での単体テスト

InMemory 実装は executor を無視してインメモリストアに直接書き込みます。`InMemoryTransactionManager` はコールバックを no-op executor で即座に呼び出します。

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

> **ロールバックのタイミング**: `SqlAlchemyTransactionManager.transactional()` は `engine.begin()` を使用します。コールバック内で例外が発生すると自動的にロールバックされます。ドメイン例外（`AccountNotFoundException` 等）はロールバック後に正常に伝播します。
