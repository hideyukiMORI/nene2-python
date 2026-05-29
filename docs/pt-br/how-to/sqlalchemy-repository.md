# Implementar um repository SQLAlchemy

Este guia mostra como escrever um `SqlAlchemyXxxRepository` que usa
`SqlAlchemyQueryExecutor` para persistência com SQL raw — sem ORM, sem mágica.

## Pré-requisitos

- Um domínio já scaffolado (`entity.py`, `repository.py`, `use_case.py`, `handler.py`)
- Um app nene2 rodando usando `AppSettings` com `DB_ADAPTER=sqlite` (ou `mysql` / `pgsql`)

---

## 1. Criar `sqlalchemy_repository.py`

### Helper de schema

Defina `ensure_schema()` no topo do arquivo.
Chame-o uma vez na inicialização a partir de `create_app()`.

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

> Coloque `ensure_schema()` em `sqlalchemy_repository.py` (não em um `schema.py` separado),
> para que a definição do schema fique ao lado do repository que possui a tabela.
> Para apps multi-domínio com um arquivo de schema compartilhado, mantenha um `ensure_schema()` por domínio
> e chame todos a partir de `create_app()`.

### Helper de linha para entidade

`fetch_one` / `fetch_all` retornam `dict[str, Any]`.
Use um método estático privado para centralizar o mapeamento e manter cada método de query enxuto.

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

> Use `dict[str, Any]` — não `dict[str, object]`.
> `fetch_one()` / `fetch_all()` retornam `dict[str, Any]`, então `row["id"]` é `Any`
> que é atribuível a `int` sob `mypy --strict` sem nenhum cast.
> Usar `dict[str, object]` requer `# type: ignore[call-overload]`
> e dispara erros `unused-ignore` subsequentes.

### Implementação completa

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

## 2. Conectar ao `create_app()`

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
        ensure_schema(executor)          # cria a tabela na primeira execução
        return SqlAlchemyBookRepository(executor)
    return InMemoryBookRepository()      # fallback para testes / desenvolvimento local
```

> Envolva o branch if/else em uma função helper como `_build_repository()` que
> retorna o tipo da interface. É mais limpo do que declarar `repo: BookRepositoryInterface`
> antes de um bloco if/else em `create_app()` — ambas as abordagens satisfazem `mypy --strict`,
> mas o helper mantém `create_app()` legível.
>
> Se preferir o branch inline, declare o tipo primeiro:
> ```python
> repo: BookRepositoryInterface
> if cfg.db_adapter == "sqlite":
>     repo = SqlAlchemyBookRepository(executor)
> else:
>     repo = InMemoryBookRepository()
> ```

> `StaticPool` é necessário para bancos SQLite em memória (`DB_NAME=:memory:`) para evitar
> que o SQLAlchemy abra múltiplas conexões — cada uma veria um banco vazio.
> SQLite baseado em arquivo e outros adaptadores não precisam disso.

---

## 3. Valor de retorno de `write()`

`executor.write()` retorna:

| Operação | Valor de retorno |
|---|---|
| `INSERT` | `lastrowid` — a chave primária inteira auto-gerada da nova linha |
| `UPDATE` / `DELETE` | `rowcount` — número de linhas afetadas (0 se nada correspondeu) |

Use `lastrowid` para reconstruir a entidade após INSERT:

```python
new_id = self._executor.write("INSERT INTO ...", {...})
return Book(id=new_id, ...)
```

Use `rowcount` para detectar linhas ausentes em UPDATE / DELETE:

```python
affected = self._executor.write("UPDATE books SET ... WHERE id = :id", {"id": book_id})
if affected == 0:
    raise BookNotFoundException(book_id)
```

> `lastrowid` é garantido como um `int` positivo para INSERTs de linha única no SQLite,
> MySQL e PostgreSQL. É `0` para INSERTs multi-linha ou quando a tabela não tem
> coluna `AUTOINCREMENT` / `SERIAL` — evite esses padrões se precisar do ID de volta.

---

## 4. Entidades com campos `datetime`

Quando sua entidade tem um campo `created_at: datetime` suportado por um
`DEFAULT CURRENT_TIMESTAMP` gerado pelo banco, use `parse_db_datetime()` de `nene2.database`.

### Por que é necessário

O SQLite armazena `CURRENT_TIMESTAMP` como uma **string simples** (`"2026-05-20 12:34:56"`),
não como um objeto Python `datetime`. `datetime.fromisoformat()` faz parse da string mas
retorna um datetime **naive** (sem timezone), então a resposta JSON vaza um timestamp ambíguo.
`parse_db_datetime()` trata todos os três casos de forma transparente:

| Driver | Valor bruto | Após `parse_db_datetime()` |
|---|---|---|
| SQLite | `"2026-05-20 12:34:56"` (str) | `datetime(…, tzinfo=UTC)` |
| MySQL/PostgreSQL | objeto `datetime` naive | `datetime(…, tzinfo=UTC)` |
| MySQL/PostgreSQL | objeto `datetime` aware | inalterado |

### Schema

```python
"created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
```

### Padrão SELECT-after-INSERT

Após `write()` você só recebe de volta o `lastrowid`, não o `created_at` gerado pelo DB.
Faça um segundo `fetch_one()` para recuperar a linha completa:

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

> O guard `if row is None: raise RuntimeError(...)` é necessário porque `fetch_one()`
> retorna `dict | None`. A linha realmente não pode ser `None` logo após INSERT — o guard
> existe para satisfazer o verificador de tipos. Prefira `RuntimeError` a `assert`: `assert`
> é removido por `python -O` e sinalizado pela regra S101 do ruff em código não-teste.

### Repository InMemory com datetime

O `InMemoryXxxRepository` deve gerar o timestamp em Python:

```python
from datetime import datetime, timezone

def save(self, title: str, body: str) -> Post:
    now = datetime.now(timezone.utc)
    post = Post(id=self._next_id, title=title, body=body, created_at=now)
    self._store[self._next_id] = post
    self._next_id += 1
    return post
```

### Serialização JSON

`datetime.isoformat()` em um datetime aware UTC produz `"2026-05-20T12:34:56+00:00"`.
Retorne-o como string no dict de resposta:

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

## 5. Recursos aninhados — validação de propriedade no DELETE

Quando um recurso é aninhado sob um pai (ex: `DELETE /posts/{post_id}/comments/{comment_id}`),
sempre valide que o filho pertence ao pai no UseCase, não apenas no banco de dados.

### Errado — ignora `post_id`

```python
# handler
@router.delete("/posts/{post_id}/comments/{comment_id}", status_code=204)
async def delete_comment(post_id: int, comment_id: int) -> None:
    delete_use_case.execute(DeleteCommentInput(comment_id))  # post_id não utilizado!
```

Isso permite que `DELETE /posts/1/comments/5` delete o comentário 5 mesmo quando ele pertence ao post 2.

### Correto — valide propriedade no UseCase

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

> O mesmo padrão se aplica a GET e PUT em recursos aninhados:
> sempre passe `post_id` para o UseCase e verifique `comment.post_id == input_.post_id`.

---

## 6. Use `InMemoryXxxRepository` nos testes

Nunca faça mock do banco de dados. Use a implementação em memória para testes unitários:

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

Para testes de repository SQLAlchemy, use um engine SQLite em memória:

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

## 7. Operações de escrita múltipla atômicas com `transactional()`

Quando um UseCase precisa escrever em múltiplas tabelas atomicamente, use `SqlAlchemyTransactionManager.transactional()` junto com métodos `_in_tx` do repository.

### Definir métodos `_in_tx` na interface

Adicione métodos dedicados que aceitam um parâmetro `executor` explícito. Esses são chamados apenas dentro de um callback `transactional()` — nunca fora.

```python
from nene2.database import DatabaseQueryExecutorInterface
from abc import ABC, abstractmethod

class AccountRepositoryInterface(ABC):
    @abstractmethod
    def find_by_id(self, account_id: int) -> Account | None: ...

    # variantes _in_tx — executor é fornecido pelo callback transactional()
    @abstractmethod
    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None: ...

    @abstractmethod
    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta_cents: int
    ) -> None: ...
```

### Implementar métodos `_in_tx` no repository SQLAlchemy

Os métodos `_in_tx` usam o `executor` passado em vez de `self._executor`, para que
compartilhem a mesma conexão e participem da mesma transação.

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

### Conectar o UseCase com `SqlAlchemyTransactionManager`

```python
from nene2.database import SqlAlchemyTransactionManager

engine = create_engine(cfg.db_url, connect_args={"check_same_thread": False})
transaction_manager = SqlAlchemyTransactionManager(engine)

transfer_use_case = TransferUseCase(transaction_manager, account_repo, transfer_repo)
```

### Implementar InMemory `_in_tx` para testes unitários

A implementação InMemory ignora o executor — as operações vão diretamente para o store em memória. `InMemoryTransactionManager` chama o callback imediatamente com um executor no-op.

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

> **Rollback em exceção**: `SqlAlchemyTransactionManager.transactional()` usa `engine.begin()` — qualquer exceção dentro do callback dispara um rollback automático. Exceções de domínio (`AccountNotFoundException`, etc.) propagam normalmente após o rollback.

---

## 6. Usando MySQL 8

### Pacotes necessários

O MySQL 8 usa autenticação `caching_sha2_password` por padrão.
Instale **ambos** `pymysql` e `cryptography` — sem `cryptography` a conexão falha com
`Authentication plugin 'caching_sha2_password' is not supported`.

```bash
uv add pymysql cryptography
```

### URL de conexão

```python
url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
engine = create_engine(url, pool_pre_ping=True)
```

`pool_pre_ping=True` é recomendado para MySQL — testa a conexão antes do uso para lidar com
conexões inativas após o `wait_timeout` do servidor.

### Health check

`DatabaseHealthCheck` recebe um **`SqlAlchemyQueryExecutor`**, não o engine diretamente:

```python
from nene2.database import DatabaseHealthCheck, SqlAlchemyQueryExecutor

executor = SqlAlchemyQueryExecutor(engine)
health = DatabaseHealthCheck(executor)   # ← executor, não engine

app.add_api_route("/health", health.check, methods=["GET"])
```

### Diferença de tipo de `CURRENT_TIMESTAMP`

O SQLite retorna `CURRENT_TIMESTAMP` como `str`; o MySQL retorna um objeto `datetime` naive.
Use `parse_db_datetime()` em `_to_entity()` para tratar ambos de forma transparente:

```python
from nene2.database import parse_db_datetime

def _to_entity(row: dict[str, Any]) -> Product:
    return Product(
        id=int(row["id"]),
        created_at=parse_db_datetime(row["created_at"]),  # funciona para SQLite e MySQL
    )
```

### Exemplo Docker Compose

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
