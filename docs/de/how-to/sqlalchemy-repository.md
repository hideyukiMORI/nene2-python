# Ein SQLAlchemy-Repository implementieren

Dieser Leitfaden zeigt, wie Sie ein `SqlAlchemyXxxRepository` schreiben, das `SqlAlchemyQueryExecutor` für Raw-SQL-Persistenz verwendet — kein ORM, keine Magie.

## Voraussetzungen

- Eine bereits erstellte Domain (`entity.py`, `repository.py`, `use_case.py`, `handler.py`)
- Eine laufende nene2-App mit `AppSettings` und `DB_ADAPTER=sqlite` (oder `mysql` / `pgsql`)

---

## 1. `sqlalchemy_repository.py` erstellen

### Schema-Helfer

Definieren Sie `ensure_schema()` am Anfang der Datei. Rufen Sie es einmal beim Start aus `create_app()` auf.

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

> Legen Sie `ensure_schema()` in `sqlalchemy_repository.py` (nicht in eine separate `schema.py`), damit die Schema-Definition neben dem Repository liegt, das die Tabelle besitzt. Für Multi-Domain-Apps mit einer gemeinsamen Schema-Datei behalten Sie ein `ensure_schema()` pro Domain und rufen Sie alle aus `create_app()` auf.

### Zeile-zu-Entity-Helfer

`fetch_one` / `fetch_all` gibt `dict[str, Any]` zurück. Verwenden Sie eine private statische Methode, um das Mapping zu zentralisieren und jede Abfragemethode schlank zu halten.

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

> Verwenden Sie `dict[str, Any]` — nicht `dict[str, object]`. `fetch_one()` / `fetch_all()` gibt `dict[str, Any]` zurück, sodass `row["id"]` `Any` ist, das unter `mypy --strict` ohne Casts `int` zugewiesen werden kann. Die Verwendung von `dict[str, object]` erfordert stattdessen `# type: ignore[call-overload]` und löst Folge-`unused-ignore`-Fehler aus.

### Vollständige Implementierung

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

## 2. In `create_app()` einbinden

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
        ensure_schema(executor)          # erstellt Tabelle beim ersten Aufruf
        return SqlAlchemyBookRepository(executor)
    return InMemoryBookRepository()      # Fallback für Tests / lokale Entwicklung
```

> Wickeln Sie den if/else-Zweig in eine Hilfsfunktion wie `_build_repository()` ein, die den Interface-Typ zurückgibt. Das ist sauberer als das Deklarieren von `repo: BookRepositoryInterface` vor einem if/else-Block in `create_app()` — beide Ansätze erfüllen `mypy --strict`, aber der Helfer hält `create_app()` lesbar.

> `StaticPool` ist für SQLite-In-Memory-Datenbanken (`DB_NAME=:memory:`) erforderlich, um zu verhindern, dass SQLAlchemy mehrere Verbindungen öffnet — von denen jede eine leere Datenbank sehen würde. Dateibasiertes SQLite und andere Adapter benötigen es nicht.

---

## 3. Rückgabewert von `write()`

`executor.write()` gibt zurück:

| Operation | Rückgabewert |
|---|---|
| `INSERT` | `lastrowid` — der automatisch generierte ganzzahlige Primärschlüssel der neuen Zeile |
| `UPDATE` / `DELETE` | `rowcount` — Anzahl der betroffenen Zeilen (0 wenn nichts zutraf) |

Verwenden Sie `lastrowid`, um die Entity nach INSERT zu rekonstruieren:

```python
new_id = self._executor.write("INSERT INTO ...", {...})
return Book(id=new_id, ...)
```

Verwenden Sie `rowcount`, um fehlende Zeilen bei UPDATE / DELETE zu erkennen:

```python
affected = self._executor.write("UPDATE books SET ... WHERE id = :id", {"id": book_id})
if affected == 0:
    raise BookNotFoundException(book_id)
```

---

## 4. Entities mit `datetime`-Feldern

Wenn Ihre Entity ein `created_at: datetime`-Feld hat, das durch ein datenbankgeneriertes `DEFAULT CURRENT_TIMESTAMP` unterstützt wird, verwenden Sie `parse_db_datetime()` aus `nene2.database`.

### Warum es benötigt wird

SQLite speichert `CURRENT_TIMESTAMP` als **einfachen String** (`"2026-05-20 12:34:56"`), nicht als Python-`datetime`-Objekt. `datetime.fromisoformat()` parst den String, gibt aber ein **naives** datetime (ohne Zeitzone) zurück, sodass die JSON-Antwort einen mehrdeutigen Zeitstempel enthält. `parse_db_datetime()` behandelt alle drei Fälle transparent:

| Treiber | Rohwert | Nach `parse_db_datetime()` |
|---|---|---|
| SQLite | `"2026-05-20 12:34:56"` (str) | `datetime(…, tzinfo=UTC)` |
| MySQL/PostgreSQL | naives `datetime`-Objekt | `datetime(…, tzinfo=UTC)` |
| MySQL/PostgreSQL | bewusstes `datetime`-Objekt | unverändert |

### SELECT-nach-INSERT-Muster

Nach `write()` erhalten Sie nur `lastrowid` zurück, nicht das DB-generierte `created_at`. Führen Sie ein zweites `fetch_one()` aus, um die vollständige Zeile abzurufen:

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

---

## 5. Verschachtelte Ressourcen — Besitzervalidierung in DELETE

Bei verschachtelten Ressourcen (z. B. `DELETE /posts/{post_id}/comments/{comment_id}`) validieren Sie immer im UseCase, dass das Kind zum Elternteil gehört, nicht nur in der Datenbank.

### Falsch — ignoriert `post_id`

```python
# handler
@router.delete("/posts/{post_id}/comments/{comment_id}", status_code=204)
async def delete_comment(post_id: int, comment_id: int) -> None:
    delete_use_case.execute(DeleteCommentInput(comment_id))  # post_id ungenutzt!
```

### Korrekt — Besitz im UseCase validieren

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

---

## 6. `InMemoryXxxRepository` in Tests verwenden

Mocken Sie die Datenbank niemals. Verwenden Sie die In-Memory-Implementierung für Unit-Tests:

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

---

## 7. Atomare Mehrfach-Schreiboperationen mit `transactional()`

Wenn ein UseCase atomar in mehrere Tabellen schreiben muss, verwenden Sie `SqlAlchemyTransactionManager.transactional()` zusammen mit `_in_tx`-Repository-Methoden.

Detaillierte Dokumentation zu Transaktionsmustern finden Sie im [SQLAlchemy-Repository How-to](sqlalchemy-repository.md) (englische Originalversion) und in der [Framework-Modulreferenz](../reference/framework-modules.md).

---

## 8. MySQL 8 verwenden

### Erforderliche Pakete

MySQL 8 verwendet standardmäßig `caching_sha2_password`-Authentifizierung. Installieren Sie **sowohl** `pymysql` als auch `cryptography` — ohne `cryptography` schlägt die Verbindung fehl mit `Authentication plugin 'caching_sha2_password' is not supported`.

```bash
uv add pymysql cryptography
```

### Verbindungs-URL

```python
url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
engine = create_engine(url, pool_pre_ping=True)
```

`pool_pre_ping=True` wird für MySQL empfohlen — es testet die Verbindung vor der Verwendung, um veraltete Verbindungen nach dem `wait_timeout` des Servers zu behandeln.
