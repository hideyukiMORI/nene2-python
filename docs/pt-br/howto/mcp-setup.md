# Guia de configuração do MCP — integração com Claude Desktop

## Visão geral

`example/mcp.py` expõe todos os UseCases de Note, Tag e Comment (15 ferramentas) como ferramentas MCP.
Uma vez configurado, o Claude Desktop e o CLI `claude` podem realizar operações CRUD diretamente.

## Pré-requisitos

- `uv sync` concluído
- Ambiente Python 3.12+

## Configuração do Claude Desktop

`claude_desktop_config.json` está localizado em:

| OS | Caminho |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

### macOS / Linux (nativo)

```json
{
  "mcpServers": {
    "nene2-example": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/nene2-python",
        "run",
        "python",
        "-m",
        "example.mcp"
      ],
      "env": {
        "DB_ADAPTER": "sqlite",
        "DB_NAME": "/path/to/nene2-python/data/nene2.db"
      }
    }
  }
}
```

Substitua `/path/to/nene2-python` pelo caminho absoluto para este repositório.

### Windows + WSL2

O Claude Desktop roda no Windows mas o projeto vive dentro do WSL2.
Use `wsl` como comando para fazer a ponte entre eles:

```json
{
  "mcpServers": {
    "nene2-example": {
      "command": "wsl",
      "args": [
        "-e", "bash", "-c",
        "cd /home/<user>/nene2-python && PYTHONPATH=src uv run python -m example.mcp"
      ],
      "env": {
        "DB_ADAPTER": "sqlite",
        "DB_NAME": "/home/<user>/nene2-python/data/nene2.db"
      }
    }
  }
}
```

> Todos os caminhos devem ser **caminhos Linux do WSL** (ex: `/home/user/...`), não caminhos do Windows.
> O `DB_NAME` também deve ser um caminho Linux para que o SQLite crie o arquivo dentro do WSL.

Para um projeto instalado via `uv add git+...` (não o próprio repositório nene2-python):

```json
{
  "mcpServers": {
    "myapp": {
      "command": "wsl",
      "args": [
        "-e", "bash", "-c",
        "cd /home/<user>/my-project && PYTHONPATH=src uv run python -m mcp_server"
      ]
    }
  }
}
```

## Ferramentas disponíveis

| Ferramenta | Descrição |
|---|---|
| `list_notes` | Listar notas com paginação |
| `get_note` | Buscar uma nota pelo ID |
| `create_note` | Criar uma nova nota |
| `update_note` | Atualizar uma nota |
| `delete_note` | Deletar uma nota |
| `list_tags` | Listar tags |
| `get_tag` | Buscar uma tag pelo ID |
| `create_tag` | Criar uma nova tag |
| `update_tag` | Atualizar uma tag |
| `delete_tag` | Deletar uma tag |
| `list_comments` | Listar comentários de uma nota |
| `get_comment` | Buscar um comentário pelo ID |
| `create_comment` | Criar um comentário em uma nota |
| `update_comment` | Atualizar um comentário |
| `delete_comment` | Deletar um comentário |

## Executando via CLI

```bash
uv run python -m example.mcp
```

O servidor escuta em stdin/stdout (transporte stdio) — padrão para MCP.

## Transporte customizado

```python
from example.mcp import create_mcp_server

server = create_mcp_server()
server.run(transport="sse")          # Server-Sent Events
server.run(transport="streamable-http")  # HTTP streaming
```

---

## Compartilhando estado entre servidor MCP e API HTTP

O servidor MCP roda como um **processo separado** da API HTTP.
`InMemoryXxxRepository` cria seu próprio store isolado por processo —
dados escritos via MCP não são visíveis para a API HTTP, e vice-versa.

Para compartilhar estado, aponte ambos os processos para o mesmo banco de dados persistente:

**API HTTP `.env`**:

```dotenv
DB_ADAPTER=sqlite
DB_NAME=/absolute/path/to/shared.db
```

**Claude Desktop `claude_desktop_config.json`**:

```json
"env": {
  "DB_ADAPTER": "sqlite",
  "DB_NAME": "/absolute/path/to/shared.db"
}
```

Ambos os processos abrem o mesmo arquivo SQLite via SQLAlchemy.
O modo WAL do SQLite trata leituras concorrentes com segurança para cargas de trabalho leves.

> Para uso em produção com alta concorrência, prefira MySQL ou PostgreSQL.
