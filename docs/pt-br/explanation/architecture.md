# Visão geral da arquitetura

## Estrutura de camadas

O nene2-python segue a Clean Architecture. As dependências fluem de fora para dentro.

```
┌─────────────────────────────────────────────┐
│  HTTP Handler (FastAPI router)              │
│  parse request → call use-case → response  │
├─────────────────────────────────────────────┤
│  UseCase                                    │
│  Lógica de negócio — sem HTTP ou DB        │
├─────────────────────────────────────────────┤
│  RepositoryInterface (ABC)                  │
│  Contrato das operações que o domínio       │
│  precisa                                    │
├─────────────────────────────────────────────┤
│  ConcreteRepository                         │
│  Implementações SQLAlchemy / InMemory       │
└─────────────────────────────────────────────┘
```

## Responsabilidades de cada camada

### HTTP Handler

- **Responsabilidade única**: parsear o request, chamar um UseCase, retornar uma response
- Usa o `BaseModel` do Pydantic para validação do corpo da requisição (apenas na fronteira HTTP)
- Contém zero lógica de domínio
- Exposto via uma função factory `make_xxx_router()`

```python
@router.post("", status_code=201)
async def create_note(body: CreateNoteBody) -> JSONResponse:
    note = create_use_case.execute(CreateNoteInput(title=body.title, body=body.body))
    return JSONResponse({"id": note.id, "title": note.title, "body": note.body}, status_code=201)
```

### UseCase

- **Responsabilidade única**: implementar uma regra de negócio
- Um método: `execute(input_: XxxInput) -> XxxOutput`
- Sem `import fastapi`, sem `import sqlalchemy`
- Não chama outros UseCases
- Testável apenas com `InMemoryRepository`

### RepositoryInterface

- Definida como ABC — o UseCase depende apenas da interface
- A mesma interface é implementada pelas versões InMemory e SQLAlchemy
- `find_all`, `find_by_id`, `save`, `update`, `delete`, `count`

### ConcreteRepository

- SQLAlchemy Core (sem ORM) com queries parametrizadas
- Queries executadas via `SqlAlchemyQueryExecutor`
- Schema da tabela: o app de exemplo usa um `src/example/schema.py` centralizado; para novos projetos, defina `ensure_schema()` no `sqlalchemy_repository.py` de cada domínio e chame cada um a partir de `create_app()`

## Pilha de middleware

As requisições passam por cada middleware do mais externo para o mais interno:

```
BearerTokenMiddleware        Autenticação (Bearer Token)
ApiKeyAuthMiddleware         Autenticação (API Key)
CORSMiddleware               CORS
ThrottleMiddleware           Rate limiting (janela fixa)
RequestSizeLimitMiddleware   Limitação de tamanho do payload
RequestLoggingMiddleware     Logging estruturado de requisições (structlog)
RequestIdMiddleware          Geração / propagação do X-Request-ID
SecurityHeadersMiddleware    Headers de segurança nas respostas
ErrorHandlerMiddleware       Exceções → RFC 9457 Problem Details
```

## Injeção de dependências

O `Depends` do FastAPI é usado apenas na fronteira HTTP. UseCases e repositories são conectados via injeção por construtor em `app.py`.

```python
# app.py — conexão das dependências
note_repo = SqlAlchemyNoteRepository(executor)
app.include_router(make_note_router(
    list_use_case=ListNotesUseCase(note_repo),
    create_use_case=CreateNoteUseCase(note_repo),
    ...
))
```

## Layout do pacote de domínio

```
src/example/<domain>/
  __init__.py
  entity.py              — @dataclass(frozen=True, slots=True)
  repository.py          — ABC + implementação InMemory
  exceptions.py          — XxxNotFoundException + ExceptionHandler
  use_case.py            — 5 UseCases + DTOs Input/Output
  handler.py             — factory do router FastAPI
  sqlalchemy_repository.py — backend SQL
```
