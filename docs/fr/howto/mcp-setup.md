# Guide de configuration MCP — intégration Claude Desktop

## Vue d'ensemble

`example/mcp.py` expose tous les UseCases Note, Tag et Comment (15 outils) comme des outils
MCP. Une fois configuré, Claude Desktop et le CLI `claude` peuvent effectuer des opérations
CRUD directement.

## Prérequis

- `uv sync` complété
- Environnement Python 3.12+

## Configuration de Claude Desktop

`claude_desktop_config.json` se trouve à :

| OS | Chemin |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

### macOS / Linux (natif)

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

Remplacez `/path/to/nene2-python` par le chemin absolu vers ce dépôt.

### Windows + WSL2

Claude Desktop fonctionne sur Windows mais le projet vit dans WSL2.
Utilisez `wsl` comme commande pour faire le pont :

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

> Tous les chemins doivent être des **chemins Linux WSL** (p. ex. `/home/user/...`), pas des
> chemins Windows. Le `DB_NAME` doit aussi être un chemin Linux pour que SQLite crée le fichier
> dans WSL.

Pour un projet installé via `uv add git+...` (pas le dépôt nene2-python lui-même) :

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

## Outils disponibles

| Outil | Description |
|---|---|
| `list_notes` | Lister les notes avec pagination |
| `get_note` | Obtenir une note par ID |
| `create_note` | Créer une nouvelle note |
| `update_note` | Modifier une note |
| `delete_note` | Supprimer une note |
| `list_tags` | Lister les tags |
| `get_tag` | Obtenir un tag par ID |
| `create_tag` | Créer un nouveau tag |
| `update_tag` | Modifier un tag |
| `delete_tag` | Supprimer un tag |
| `list_comments` | Lister les commentaires d'une note |
| `get_comment` | Obtenir un commentaire par ID |
| `create_comment` | Créer un commentaire sur une note |
| `update_comment` | Modifier un commentaire |
| `delete_comment` | Supprimer un commentaire |

## Démarrer via CLI

```bash
uv run python -m example.mcp
```

Le serveur écoute sur stdin/stdout (transport stdio) — standard pour MCP.

## Transport personnalisé

```python
from example.mcp import create_mcp_server

server = create_mcp_server()
server.run(transport="sse")          # Server-Sent Events
server.run(transport="streamable-http")  # HTTP streaming
```

---

## Partager l'état entre le serveur MCP et l'API HTTP

Le serveur MCP s'exécute comme un **processus séparé** de l'API HTTP.
`InMemoryXxxRepository` crée son propre store isolé par processus — les données écrites via
MCP ne sont pas visibles pour l'API HTTP, et vice versa.

Pour partager l'état, pointez les deux processus sur la même base de données persistante :

**Fichier `.env` de l'API HTTP** :

```dotenv
DB_ADAPTER=sqlite
DB_NAME=/absolute/path/to/shared.db
```

**`claude_desktop_config.json` de Claude Desktop** :

```json
"env": {
  "DB_ADAPTER": "sqlite",
  "DB_NAME": "/absolute/path/to/shared.db"
}
```

Les deux processus ouvrent le même fichier SQLite via SQLAlchemy.
Le mode WAL de SQLite gère les lectures concurrentes de façon sûre pour les charges légères.

> Pour une utilisation en production à forte concurrence, préférez MySQL ou PostgreSQL.
