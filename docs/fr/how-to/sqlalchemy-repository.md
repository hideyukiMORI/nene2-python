# Implémenter un repository SQLAlchemy

Ce guide montre comment écrire un `SqlAlchemyXxxRepository` qui utilise
`SqlAlchemyQueryExecutor` pour la persistance SQL brut — sans ORM, sans magie.

## Prérequis

- Un domaine déjà scaffoldé (`entity.py`, `repository.py`, `use_case.py`, `handler.py`)
- Une application nene2 qui tourne, utilisant `AppSettings` avec `DB_ADAPTER=sqlite` (ou `mysql` / `pgsql`)

---

## 1. Créer `sqlalchemy_repository.py`

### Helper de schéma

Définissez `ensure_schema()` en haut du fichier.
Appelez-le une fois au démarrage depuis `create_app()`.

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

> Mettez `ensure_schema()` dans `sqlalchemy_repository.py` (pas dans un `schema.py` séparé),
> afin que la définition du schéma vive à côté du repository qui possède la table.
> Pour les applications multi-domaines avec un fichier de schéma partagé, gardez un
> `ensure_schema()` par domaine et appelez-les tous depuis `create_app()`.

### Helper ligne-vers-entité

`fetch_one` / `fetch_all` retournent `dict[str, Any]`.
Utilisez une méthode statique privée pour centraliser le mapping et garder chaque méthode
de requête concise.

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

> Utilisez `dict[str, Any]` — pas `dict[str, object]`.
> `fetch_one()` / `fetch_all()` retournent `dict[str, Any]`, donc `row["id"]` est `Any`
> qui est assignable à `int` sous `mypy --strict` sans aucun cast.
> Utiliser `dict[str, object]` à la place nécessite `# type: ignore[call-overload]`
> et déclenche des erreurs `unused-ignore` de suivi.

### Implémentation complète

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

## 2. Câbler dans `create_app()`

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
        ensure_schema(executor)          # crée la table au premier démarrage
        return SqlAlchemyBookRepository(executor)
    return InMemoryBookRepository()      # fallback pour les tests / dev local
```

> Encapsulez la branche if/else dans une fonction helper comme `_build_repository()` qui
> retourne le type d'interface. C'est plus propre que de déclarer `repo: BookRepositoryInterface`
> avant un bloc if/else dans `create_app()` — les deux approches satisfont `mypy --strict`,
> mais le helper garde `create_app()` lisible.
>
> Si vous préférez le branchement inline, déclarez le type en premier :
> ```python
> repo: BookRepositoryInterface
> if cfg.db_adapter == "sqlite":
>     repo = SqlAlchemyBookRepository(executor)
> else:
>     repo = InMemoryBookRepository()
> ```

> `StaticPool` est requis pour les bases SQLite en mémoire (`DB_NAME=:memory:`) pour empêcher
> SQLAlchemy d'ouvrir plusieurs connexions — chacune verrait une base de données vide.
> SQLite basé sur des fichiers et les autres adaptateurs n'en ont pas besoin.

---

## 3. Valeur de retour de `write()`

`executor.write()` retourne :

| Opération | Valeur de retour |
|---|---|
| `INSERT` | `lastrowid` — la clé primaire entière auto-générée de la nouvelle ligne |
| `UPDATE` / `DELETE` | `rowcount` — nombre de lignes affectées (0 si rien ne correspondait) |

Utilisez `lastrowid` pour reconstruire l'entité après INSERT :

```python
new_id = self._executor.write("INSERT INTO ...", {...})
return Book(id=new_id, ...)
```

Utilisez `rowcount` pour détecter les lignes manquantes sur UPDATE / DELETE :

```python
affected = self._executor.write("UPDATE books SET ... WHERE id = :id", {"id": book_id})
if affected == 0:
    raise BookNotFoundException(book_id)
```

> `lastrowid` est garanti être un `int` positif pour les INSERTs d'une seule ligne sur SQLite,
> MySQL et PostgreSQL. Il vaut `0` pour les INSERTs multi-lignes ou quand la table n'a pas de
> colonne `AUTOINCREMENT` / `SERIAL` — évitez ces schémas si vous avez besoin de l'ID en retour.

---

## 4. Entités avec des champs `datetime`

Quand votre entité a un champ `created_at: datetime` soutenu par un
`DEFAULT CURRENT_TIMESTAMP` généré par la base de données, utilisez `parse_db_datetime()`
depuis `nene2.database`.

### Pourquoi c'est nécessaire

SQLite stocke `CURRENT_TIMESTAMP` comme une **chaîne brute** (`"2026-05-20 12:34:56"`),
pas comme un objet Python `datetime`. `datetime.fromisoformat()` analyse la chaîne mais retourne
un datetime **naïf** (sans fuseau horaire), donc la réponse JSON fuit un timestamp ambigu.
`parse_db_datetime()` gère les trois cas de manière transparente :

| Driver | Valeur brute | Après `parse_db_datetime()` |
|---|---|---|
| SQLite | `"2026-05-20 12:34:56"` (str) | `datetime(…, tzinfo=UTC)` |
| MySQL/PostgreSQL | objet `datetime` naïf | `datetime(…, tzinfo=UTC)` |
| MySQL/PostgreSQL | objet `datetime` aware | inchangé |

### Schéma

```python
"created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
```

### Schéma SELECT-après-INSERT

Après `write()` vous n'obtenez que le `lastrowid`, pas le `created_at` généré par la DB.
Faites un second `fetch_one()` pour récupérer la ligne complète :

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

> Le garde `if row is None: raise RuntimeError(...)` est nécessaire car `fetch_one()` retourne
> `dict | None`. La ligne ne peut pas réellement être `None` juste après un INSERT — le garde
> existe pour satisfaire le vérificateur de types. Préférez `RuntimeError` à `assert` : `assert`
> est supprimé par `python -O` et signalé par la règle S101 de ruff dans le code hors test.

### Repository InMemory avec datetime

Le `InMemoryXxxRepository` doit générer le timestamp en Python :

```python
from datetime import datetime, timezone

def save(self, title: str, body: str) -> Post:
    now = datetime.now(timezone.utc)
    post = Post(id=self._next_id, title=title, body=body, created_at=now)
    self._store[self._next_id] = post
    self._next_id += 1
    return post
```

### Sérialisation JSON

`datetime.isoformat()` sur un datetime UTC-aware produit `"2026-05-20T12:34:56+00:00"`.
Retournez-le comme une chaîne dans le dict de réponse :

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

## 5. Ressources imbriquées — validation de propriété dans DELETE

Quand une ressource est imbriquée sous un parent (p. ex. `DELETE /posts/{post_id}/comments/{comment_id}`),
validez toujours que l'enfant appartient au parent dans le UseCase, pas seulement dans la base de données.

### Incorrect — ignore `post_id`

```python
# handler
@router.delete("/posts/{post_id}/comments/{comment_id}", status_code=204)
async def delete_comment(post_id: int, comment_id: int) -> None:
    delete_use_case.execute(DeleteCommentInput(comment_id))  # post_id inutilisé !
```

Cela permet à `DELETE /posts/1/comments/5` de supprimer le commentaire 5 même s'il appartient
au post 2.

### Correct — valider la propriété dans le UseCase

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

> Le même schéma s'applique à GET et PUT sur les ressources imbriquées :
> passez toujours `post_id` dans le UseCase et vérifiez `comment.post_id == input_.post_id`.

---

## 6. Utiliser `InMemoryXxxRepository` dans les tests

Ne moquez jamais la base de données. Utilisez l'implémentation en mémoire pour les tests unitaires :

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

Pour les tests du repository SQLAlchemy, utilisez un moteur SQLite en mémoire :

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

## 7. Opérations multi-écritures atomiques avec `transactional()`

Quand un UseCase doit écrire dans plusieurs tables de façon atomique, utilisez
`SqlAlchemyTransactionManager.transactional()` avec des méthodes de repository `_in_tx`.

### Définir les méthodes `_in_tx` sur l'interface

Ajoutez des méthodes dédiées qui acceptent un paramètre `executor` explicite. Celles-ci sont
appelées uniquement dans un callback `transactional()` — jamais en dehors.

```python
from nene2.database import DatabaseQueryExecutorInterface
from abc import ABC, abstractmethod

class AccountRepositoryInterface(ABC):
    @abstractmethod
    def find_by_id(self, account_id: int) -> Account | None: ...

    # variantes _in_tx — executor est fourni par le callback transactional()
    @abstractmethod
    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None: ...

    @abstractmethod
    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta_cents: int
    ) -> None: ...
```

### Implémenter les méthodes `_in_tx` dans le repository SQLAlchemy

Les méthodes `_in_tx` utilisent l'`executor` passé plutôt que `self._executor`, de sorte
qu'elles partagent la même connexion et participent à la même transaction.

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

### Câbler le UseCase avec `SqlAlchemyTransactionManager`

```python
from nene2.database import SqlAlchemyTransactionManager

engine = create_engine(cfg.db_url, connect_args={"check_same_thread": False})
transaction_manager = SqlAlchemyTransactionManager(engine)

transfer_use_case = TransferUseCase(transaction_manager, account_repo, transfer_repo)
```

### Implémenter InMemory `_in_tx` pour les tests unitaires

L'implémentation InMemory ignore l'executor — les opérations vont directement dans le store
en mémoire. `InMemoryTransactionManager` appelle le callback immédiatement avec un executor
no-op.

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

> **Rollback sur exception** : `SqlAlchemyTransactionManager.transactional()` utilise
> `engine.begin()` — toute exception dans le callback déclenche un rollback automatique. Les
> exceptions de domaine (`AccountNotFoundException`, etc.) se propagent normalement après le rollback.

---

## 6. Utiliser MySQL 8

### Packages requis

MySQL 8 utilise l'authentification `caching_sha2_password` par défaut.
Installez **les deux** `pymysql` et `cryptography` — sans `cryptography`, la connexion échoue avec
`Authentication plugin 'caching_sha2_password' is not supported`.

```bash
uv add pymysql cryptography
```

### URL de connexion

```python
url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
engine = create_engine(url, pool_pre_ping=True)
```

`pool_pre_ping=True` est recommandé pour MySQL — il teste la connexion avant utilisation pour
gérer les connexions périmées après le `wait_timeout` du serveur.

### Health check

`DatabaseHealthCheck` prend un **`SqlAlchemyQueryExecutor`**, pas le moteur directement :

```python
from nene2.database import DatabaseHealthCheck, SqlAlchemyQueryExecutor

executor = SqlAlchemyQueryExecutor(engine)
health = DatabaseHealthCheck(executor)   # ← executor, pas engine

app.add_api_route("/health", health.check, methods=["GET"])
```

### Différence de type `CURRENT_TIMESTAMP`

SQLite retourne `CURRENT_TIMESTAMP` comme une `str` ; MySQL retourne un objet `datetime` naïf.
Utilisez `parse_db_datetime()` dans `_to_entity()` pour gérer les deux de manière transparente :

```python
from nene2.database import parse_db_datetime

def _to_entity(row: dict[str, Any]) -> Product:
    return Product(
        id=int(row["id"]),
        created_at=parse_db_datetime(row["created_at"]),  # fonctionne pour SQLite et MySQL
    )
```

### Exemple Docker Compose

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
