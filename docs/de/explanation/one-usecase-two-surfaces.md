# Ein UseCase, zwei Oberflächen (HTTP + MCP)

Das Kernversprechen von NENE2 lautet **„LLM Delivery Ready"**: Dieselbe Domänenlogik wird sowohl als JSON-HTTP-API für Anwendungen *als auch* als [MCP](https://modelcontextprotocol.io/)-Tools für LLM-Agenten ausgeliefert — einmal geschrieben, ohne Duplizierung pro Oberfläche. Diese Seite zeigt genau wie, anhand der Referenzanwendung.

## Der gemeinsame Kern

Die Domänenlogik lebt in **UseCase**-Klassen, die nichts über FastAPI oder SQLAlchemy wissen ([`src/example/note/use_case.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/note/use_case.py)). Beide Oberflächen konstruieren denselben UseCase und rufen `.execute()` auf:

**HTTP** — [`src/example/note/handler.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/note/handler.py):

```python
@router.post("", status_code=201, response_model=NoteResponse, summary="Create a note")
async def create_note(body: CreateNoteBody) -> NoteResponse:
    note = create_use_case.execute(CreateNoteInput(body.title, body.body))
    return NoteResponse(id=note.id, title=note.title, body=note.body)
```

Der Handler ist reines *parse → use-case → response*: Er enthält keine Domänenregeln. Die Längen- und Nicht-Leer-Prüfungen leben in `CreateNoteInput` (unten), sodass sie unabhängig von der aufgerufenen Oberfläche gelten.

**MCP** — [`src/example/mcp.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/mcp.py):

```python
@server.tool("Create a new note.")
def create_note(title: str, body: str) -> dict:
    return asdict(note_create.execute(CreateNoteInput(title=title, body=body)))
```

Derselbe `CreateNoteUseCase`, dasselbe `CreateNoteInput`, dasselbe Repository — nur die **Kante** unterscheidet sich. Die UseCase-`Input`/`Output`-DTOs *sind* der Vertrag für beide Oberflächen; FastMCP leitet das Tool-Schema aus der Funktionssignatur ab, FastAPI leitet das OpenAPI-Schema aus dem Pydantic-Body und `response_model` ab.

## Was das bringt

- Domäne **einmal** schreiben und testen; aus demselben Codepfad sowohl an Anwendungen (HTTP) als auch an Agenten (MCP) ausliefern.
- Ein im UseCase behobener Fehler ist auf **beiden** Oberflächen gleichzeitig behoben.
- Neue Domains sind für Agenten erreichbar, sobald ihre UseCases existieren — `mcp.py` verdrahtet 15 Tools (Note / Tag / Comment) ohne zusätzliche Infrastruktur.

## Nachweis (ein Test, keine Behauptung)

[`tests/example/test_http_mcp_parity.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/tests/example/test_http_mcp_parity.py) verdrahtet eine HTTP-App und einen MCP-Server auf demselben SQLite-Store und prüft, dass die Oberflächen austauschbar sind:

- Eine über das MCP-Tool `create_note` erstellte Notiz ist über `GET /examples/notes/{id}` lesbar,
- Eine über HTTP `POST /examples/notes` erstellte Notiz ist über das MCP-Tool `get_note` lesbar,
- Beide Schreibvorgänge landen in einem Store.

Dies sichert das Alleinstellungsmerkmal als Regressionstest — wenn die beiden Oberflächen jemals auseinanderdriften, schlägt die CI fehl.

## Was geteilt wird und was nicht

Die Trennlinie ist **Domänenregel vs. Transportmechanik**. Alles, was für eine Notiz unabhängig von der Eingangsart wahr sein muss, lebt im UseCase-Input-DTO und wird daher auf beiden Oberflächen durchgesetzt; Protokoll-Infrastruktur bleibt an der Kante.

| Belang | Wo er lebt | Mit MCP geteilt? |
|---|---|---|
| Längenbeschränkungen (`max_length`), Nicht-Leer | `CreateNoteInput.__post_init__` in `use_case.py` | **Ja** |
| Erstellen/Lesen/Aktualisieren/Löschen-Logik, Not-found-Semantik | UseCase + Entity | **Ja** |
| Anfrage-Parsing, Argument-Form/Typen | Pydantic-Body (HTTP) / FastMCP-Signatur (MCP) | Jede Oberfläche selbst |
| Authentifizierung, CORS, Throttling | Middleware in `app.py` | Nein |
| Paginierungs-Parsing, RFC 9457-Fehlerformatierung | HTTP-Schicht | Nein |

Der HTTP-`CreateNoteBody` spiegelt `max_length` über dieselbe `MAX_NOTE_TITLE_LENGTH`-Konstante — sodass das Limit einmal deklariert, in OpenAPI dokumentiert *und* in der Domain für den MCP-Pfad durchgesetzt wird.

Dies ist das **API-first / dünne-HTTP-Schicht**-Prinzip in Aktion: Die Kante passt jedes Protokoll an, das Zentrum hält die Domäne. Die praktische Regel für Implementierer:

> Wenn eine Regel für **beide** Oberflächen gelten muss, legen Sie sie in den UseCase oder die Entity — nicht in den Handler. Eine Prüfung, die nur im HTTP-Handler lebt, schützt das MCP-Tool **nicht**. (Genau deshalb wurden die Längen- und Nicht-Leer-Prüfungen in die Input-DTOs verschoben — siehe Paritätstests.)

## Siehe auch

- [Designphilosophie → LLM Delivery Ready](design-philosophy.md)
- [Architekturübersicht](architecture.md)
- [ADR 0011 — MCP als Kernabhängigkeit](../adr/0011-mcp-as-core-dependency.md)
- [MCP-Server einrichten](../howto/mcp-setup.md)
