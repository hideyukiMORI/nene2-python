# Adicionar um novo domínio

Um checklist para adicionar um novo domínio seguindo o mesmo padrão de Note, Tag e Comment.

## Checklist

### 1. Criar o pacote do domínio

```bash
mkdir -p src/example/<domain>
touch src/example/<domain>/__init__.py
```

### 2. Criar cada arquivo

| Arquivo | Conteúdo |
|---|---|
| `entity.py` | Entidade como `@dataclass(frozen=True, slots=True)` |
| `repository.py` | `XxxRepositoryInterface(ABC)` + `InMemoryXxxRepository` |
| `exceptions.py` | `XxxNotFoundException` + `XxxNotFoundExceptionHandler` |
| `use_case.py` | 5 UseCases (List / Get / Create / Update / Delete) + DTOs Input/Output |
| `handler.py` | `make_xxx_router()` — parse → use-case → response |
| `sqlalchemy_repository.py` | Implementação backend SQL |

### 3. Adicionar a tabela ao schema.py

Adicione uma chamada `CREATE TABLE` ao `ensure_schema()` em `src/example/schema.py`.

```python
executor.write(
    "CREATE TABLE IF NOT EXISTS your_domain ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "name TEXT NOT NULL,"
    "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
    ")"
)
```

### 4. Conectar ao app.py

Atualize `_build_repositories()` e `create_app()` em `src/example/app.py`.

```python
# Adicionar ao retorno de _build_repositories()
your_repo = SqlAlchemyYourRepository(executor)

# Registrar o router em create_app()
app.include_router(make_your_router(
    list_use_case=ListYourUseCase(your_repo),
    ...
))
```

### 5. Escrever os testes

```
tests/example/<domain>/
  __init__.py
  test_<domain>_use_case.py     # testes unitários do UseCase (sem DB)
  test_<domain>_repository.py   # testes de contrato do Repository (InMemory + SQLAlchemy)
  test_<domain>_http.py         # testes de integração HTTP (TestClient)
```

### 6. Registrar ferramentas MCP (opcional)

Adicione os registros de UseCase ao `create_mcp_server()` em `src/example/mcp.py`.

### 7. Passar todas as verificações

```bash
uv run pytest && \
uv run mypy src/ && \
uv run ruff check src/ tests/ && \
uv run ruff format --check src/ tests/
```

## Convenções de nomenclatura

| Alvo | Convenção | Exemplo |
|---|---|---|
| Classe Entity | PascalCase | `Note`, `Tag`, `Comment` |
| DTO de entrada do UseCase | `XxxInput` | `CreateNoteInput` |
| Exceção | `XxxNotFoundException` | `NoteNotFoundException` |
| Factory do handler | `make_xxx_router()` | `make_note_router()` |

## Implementações de referência

- `src/example/note/` — domínio CRUD básico
- `src/example/comment/` — domínio aninhado com chave estrangeira (`note_id`)
