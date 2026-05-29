# Executar testes

## Comandos básicos

```bash
# Executar todos os testes com cobertura
uv run pytest

# Saída verbosa em caso de falha
uv run pytest --tb=short -v

# Executar um diretório específico
uv run pytest tests/example/note/

# Gerar um relatório de cobertura HTML
uv run pytest --cov=src --cov-report=html
# → abra htmlcov/index.html no navegador
```

## Layout dos testes

```
tests/
  nene2/              Testes unitários do core do framework
    use_case/         Conformidade com UseCaseProtocol
    auth/             Middleware de auth e verificadores
    database/         Testes do TransactionManager
    mcp/              Testes do McpHttpClient
    middleware/       Cada middleware em isolamento
  example/
    note/             Testes do domínio Note
      test_list_notes.py           Testes unitários do UseCase
      test_note_repository.py      Testes de contrato do Repository
      test_async_note_use_case.py  Testes de UseCase async
    comment/
      test_comment_use_case.py     Testes unitários do UseCase (sem DB)
      test_comment_repository.py   Testes de contrato InMemory + SQLAlchemy
      test_comment_http.py         Testes de integração HTTP (TestClient)
```

## Tipos de teste

### Testes unitários do UseCase

Sem banco de dados, sem HTTP — use repositories InMemory. O mais rápido.

```python
def test_create_note() -> None:
    repo = InMemoryNoteRepository()
    note = CreateNoteUseCase(repo).execute(CreateNoteInput(title="t", body="b"))
    assert note.title == "t"
```

### Testes de contrato do Repository

`@pytest.fixture(params=["inmemory", "sqlalchemy"])` executa as mesmas asserções contra ambas as implementações.

```python
@pytest.fixture(params=["inmemory", "sqlalchemy"])
def repo(request): ...

def test_save_and_find(repo) -> None:
    note = repo.save("title", "body")
    assert repo.find_by_id(note.id) == note
```

### Testes de integração HTTP

Use o `TestClient` do FastAPI. Testa a pilha completa do HTTP ao repository.

```python
def test_create_note_returns_201() -> None:
    client = TestClient(create_app(AppSettings(throttle_enabled=False)))
    response = client.post("/notes", json={"title": "t", "body": "b"})
    assert response.status_code == 201
```

### Testes async

`asyncio_mode = "auto"` está definido em `pyproject.toml`, então `async def test_*` funciona diretamente.

```python
async def test_async_list_notes() -> None:
    repo = InMemoryNoteRepository()
    result = await AsyncListNotesUseCase(repo).execute(ListNotesInput(limit=10, offset=0))
    assert result.total == 0
```

## SQLite em memória para testes de integração

Ao usar `SqlAlchemyQueryExecutor` ou `SqlAlchemyTransactionManager` com um banco SQLite em memória,
sempre passe `poolclass=StaticPool`. Sem isso, o SQLAlchemy pode abrir uma nova conexão física que
vê um banco vazio.

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

`StaticPool` garante que todas as conexões lógicas compartilham a mesma conexão SQLite
subjacente, então tabelas criadas em uma operação são visíveis na próxima.

**Aplicação de chaves estrangeiras no SQLite**: o SQLite desabilita restrições de chave estrangeira
por padrão. Habilite-as com `PRAGMA foreign_keys=ON` logo após criar o engine:

```python
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("PRAGMA foreign_keys=ON"))
```

Com `StaticPool`, uma única chamada se aplica à conexão compartilhada, então todas as
operações subsequentes veem as restrições FK aplicadas.

## Capturando saída do structlog com caplog

Chame `configure_for_testing()` no nível do módulo em `conftest.py` para rotear o structlog
pelo bridge de logging da stdlib para que o fixture `caplog` do pytest possa capturá-lo.

```python
# conftest.py
from nene2.log import configure_for_testing
configure_for_testing()
```

Então faça asserções sobre strings de mensagem nos testes:

```python
def test_handler_logs(caplog: pytest.LogCaptureFixture) -> None:
    client = TestClient(create_app())
    client.post("/api/echo", json={"message": "hello"})
    assert any("processing echo" in r.message for r in caplog.records)
```

**Nota**: `caplog.records` retorna objetos `LogRecord` da stdlib. Campos vinculados com
`structlog.contextvars.bind_contextvars()` (como `request_id`) não são diretamente
acessíveis como `record.request_id` — eles aparecem como parte da string de mensagem formatada.

## TestClient HTTP métodos e parâmetro json

O `.get()`, `.post()`, `.put()`, `.patch()` do `TestClient` aceitam o parâmetro `json=`, mas
`.delete()` não (`TypeError`). Para DELETE com body, use `.request()`.

```python
# ✅ GET/POST/PUT/PATCH aceitam json=
r = client.post("/items", json={"name": "Alice"})
r = client.put("/items/1", json={"name": "Bob"})

# ❌ DELETE não aceita json=
r = client.delete("/items/bulk", json={"ids": [1, 2]})  # TypeError

# ✅ DELETE + body: use request()
r = client.request("DELETE", "/items/bulk", json={"ids": [1, 2]})
```

**Nota de design**: ter um body no DELETE é "não recomendado" pelo RFC 9110 (alguns servidores
o ignoram). Como alternativa para deleção em lote, considere o padrão `POST /items/bulk-delete`.

---

## Requisitos de cobertura

| Escopo | Meta |
|---|---|
| Geral | ≥ 80% (aplicado pela CI via `pytest --cov-fail-under=80`) |
| UseCase / Domínio | ≥ 90% (aplicado pela CI em `example/*/use_case.py`, `entity.py`, `async_use_case.py`) |

Linha de base atual: **466 testes**, ~93% de cobertura geral.

## Análise estática

```bash
uv run mypy src/          # Verificação de tipos (strict)
uv run ruff check src/ tests/    # Lint
uv run ruff format --check src/ tests/  # Verificação de formatação
uv run pip-audit --ignore-vuln PYSEC-2025-183  # Scan de dependências (igual à CI)
```

A CI executa no **Python 3.12 e 3.14** (veja `.github/workflows/ci.yml`).
