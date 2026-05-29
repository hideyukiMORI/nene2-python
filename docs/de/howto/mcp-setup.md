# MCP-Einrichtungsanleitung — Claude Desktop-Integration

## Übersicht

`example/mcp.py` stellt alle Note-, Tag- und Comment-UseCases (15 Tools) als MCP-Tools bereit. Nach der Konfiguration können Claude Desktop und das `claude`-CLI CRUD-Operationen direkt ausführen.

## Voraussetzungen

- `uv sync` abgeschlossen
- Python 3.12+-Umgebung

## Claude Desktop-Konfiguration

`claude_desktop_config.json` befindet sich unter:

| Betriebssystem | Pfad |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

### macOS / Linux (nativ)

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

Ersetzen Sie `/path/to/nene2-python` durch den absoluten Pfad zu diesem Repository.

### Windows + WSL2

Claude Desktop läuft auf Windows, aber das Projekt befindet sich innerhalb von WSL2. Verwenden Sie `wsl` als Befehl, um sie zu verbinden:

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

> Alle Pfade müssen **WSL-Linux-Pfade** sein (z. B. `/home/user/...`), keine Windows-Pfade. `DB_NAME` muss ebenfalls ein Linux-Pfad sein, damit SQLite die Datei innerhalb von WSL erstellt.

Für ein Projekt, das über `uv add git+...` installiert wurde (nicht das nene2-python-Repository selbst):

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

## Verfügbare Tools

| Tool | Beschreibung |
|---|---|
| `list_notes` | Notizen mit Paginierung auflisten |
| `get_note` | Eine Notiz nach ID abrufen |
| `create_note` | Eine neue Notiz erstellen |
| `update_note` | Eine Notiz aktualisieren |
| `delete_note` | Eine Notiz löschen |
| `list_tags` | Tags auflisten |
| `get_tag` | Einen Tag nach ID abrufen |
| `create_tag` | Einen neuen Tag erstellen |
| `update_tag` | Einen Tag aktualisieren |
| `delete_tag` | Einen Tag löschen |
| `list_comments` | Kommentare zu einer Notiz auflisten |
| `get_comment` | Einen Kommentar nach ID abrufen |
| `create_comment` | Einen Kommentar zu einer Notiz erstellen |
| `update_comment` | Einen Kommentar aktualisieren |
| `delete_comment` | Einen Kommentar löschen |

## Über CLI ausführen

```bash
uv run python -m example.mcp
```

Der Server lauscht auf stdin/stdout (stdio-Transport) — Standard für MCP.

## Benutzerdefinierter Transport

```python
from example.mcp import create_mcp_server

server = create_mcp_server()
server.run(transport="sse")          # Server-Sent Events
server.run(transport="streamable-http")  # HTTP-Streaming
```

---

## Zustand zwischen MCP-Server und HTTP-API teilen

Der MCP-Server läuft als **separater Prozess** von der HTTP-API. `InMemoryXxxRepository` erstellt pro Prozess einen eigenen isolierten Store — Daten, die über MCP geschrieben werden, sind für die HTTP-API nicht sichtbar und umgekehrt.

Um den Zustand zu teilen, zeigen Sie beide Prozesse auf dieselbe persistente Datenbank:

**HTTP-API `.env`**:

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

Beide Prozesse öffnen dieselbe SQLite-Datei über SQLAlchemy. SQLites WAL-Modus behandelt gleichzeitige Lesevorgänge sicher für leichte Workloads.

> Für hochnebenläufige Produktionsnutzung bevorzugen Sie MySQL oder PostgreSQL.
