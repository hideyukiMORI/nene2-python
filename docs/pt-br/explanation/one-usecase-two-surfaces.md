# Um UseCase, duas superfícies (HTTP + MCP)

A promessa central do NENE2 é ser **"LLM delivery ready"**: a mesma lógica de domínio é
entregue tanto como uma API JSON HTTP para aplicações *quanto* como ferramentas
[MCP](https://modelcontextprotocol.io/) para agentes LLM — escrita uma vez, sem
duplicação por superfície. Esta página mostra exatamente como, no app de referência.

## O núcleo compartilhado

A lógica de domínio vive em classes **UseCase** que não conhecem nada sobre FastAPI ou
SQLAlchemy ([`src/example/note/use_case.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/note/use_case.py)).
Ambas as superfícies constroem o *mesmo* UseCase e chamam `.execute()`:

**HTTP** — [`src/example/note/handler.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/note/handler.py):

```python
@router.post("", status_code=201, response_model=NoteResponse, summary="Create a note")
async def create_note(body: CreateNoteBody) -> NoteResponse:
    note = create_use_case.execute(CreateNoteInput(body.title, body.body))
    return NoteResponse(id=note.id, title=note.title, body=note.body)
```

O handler é puro *parse → use-case → response*: não carrega regras de domínio. As
verificações de comprimento e não-vazio vivem em `CreateNoteInput` (abaixo), então valem
independentemente de qual superfície chamou.

**MCP** — [`src/example/mcp.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/mcp.py):

```python
@server.tool("Create a new note.")
def create_note(title: str, body: str) -> dict:
    return asdict(note_create.execute(CreateNoteInput(title=title, body=body)))
```

Mesmo `CreateNoteUseCase`, mesmo `CreateNoteInput`, mesmo repository — apenas a
**borda** é diferente. Os DTOs `Input`/`Output` do UseCase *são* o contrato para ambas
as superfícies; o FastMCP deriva o schema da ferramenta da assinatura da função, o FastAPI
deriva o schema OpenAPI do corpo Pydantic e do `response_model`.

## O que isso traz

- Escreva e teste o domínio **uma vez**; entregue-o para apps (HTTP) e para agentes
  (MCP) pelo mesmo caminho de código.
- Um bug corrigido no UseCase é corrigido nas **duas** superfícies simultaneamente.
- Novos domínios são alcançáveis por agentes no momento em que seus UseCases existem —
  `mcp.py` conecta 15 ferramentas (Note / Tag / Comment) sem plumbing extra.

## Prova (um teste, não uma afirmação)

[`tests/example/test_http_mcp_parity.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/tests/example/test_http_mcp_parity.py)
conecta um app HTTP e um servidor MCP ao **mesmo** store SQLite e verifica que
as superfícies são intercambiáveis:

- uma nota criada pela ferramenta MCP `create_note` é legível via `GET /examples/notes/{id}`,
- uma nota criada via HTTP `POST /examples/notes` é legível pela ferramenta MCP `get_note`,
- ambas as escritas chegam em um único store.

Isso protege o diferencial como um teste de regressão — se as duas superfícies divergirem,
a CI falha.

## O que é compartilhado e o que não é

A linha divisória é **regra de domínio vs. mecânica de transporte**. Tudo que deve ser
verdadeiro sobre uma nota independentemente de como chegou vive no DTO Input do UseCase e
é, portanto, aplicado em ambas as superfícies; o plumbing de protocolo fica na borda.

| Preocupação | Onde vive | Compartilhada com MCP? |
|---|---|---|
| Limites de comprimento (`max_length`), não-vazio | `CreateNoteInput.__post_init__` em `use_case.py` | **Sim** |
| Lógica de create / read / update / delete, semântica de not-found | UseCase + entity | **Sim** |
| Parse de request, forma/tipos dos argumentos | Corpo Pydantic (HTTP) / assinatura FastMCP (MCP) | Cada superfície tem o seu |
| Autenticação, CORS, throttling | middleware em `app.py` | Não |
| Parse de paginação, formatação de erros RFC 9457 | Camada HTTP | Não |

O `CreateNoteBody` HTTP espelha `max_length` via a mesma constante
`MAX_NOTE_TITLE_LENGTH` — então o limite é declarado uma vez, documentado no
OpenAPI, *e* aplicado no domínio para o caminho MCP.

Este é o princípio **API-first / thin-HTTP-layer** em ação: a borda adapta
cada protocolo, o centro mantém o domínio. A regra prática para implementadores:

> Se uma regra deve valer para **ambas** as superfícies, coloque-a no UseCase ou na entity —
> não no handler. Uma verificação que vive apenas no handler HTTP **não**
> protege a ferramenta MCP. (É exatamente por isso que as verificações de comprimento e
> não-vazio foram movidas para os DTOs Input — veja os testes de paridade.)

## Veja também

- [Filosofia de design → LLM Delivery Ready](design-philosophy.md)
- [Visão geral da arquitetura](architecture.md)
- [ADR 0011 — MCP as a core dependency](../adr/0011-mcp-as-core-dependency.md)
- [Como configurar o servidor MCP](../howto/mcp-setup.md)
