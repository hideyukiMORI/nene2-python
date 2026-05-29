# Un UseCase, deux surfaces (HTTP + MCP)

La promesse centrale de NENE2 est d'être **"prêt pour la livraison LLM"** : la même logique de
domaine est délivrée à la fois comme une API JSON HTTP pour les applications *et* comme des outils
[MCP](https://modelcontextprotocol.io/) pour les agents LLM — écrite une seule fois, sans duplication
par surface. Cette page montre précisément comment, dans l'application de référence.

## Le noyau partagé

La logique de domaine vit dans des classes **UseCase** qui ne savent rien de FastAPI ou de
SQLAlchemy ([`src/example/note/use_case.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/note/use_case.py)).
Les deux surfaces construisent le *même* UseCase et appellent `.execute()` :

**HTTP** — [`src/example/note/handler.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/note/handler.py) :

```python
@router.post("", status_code=201, response_model=NoteResponse, summary="Create a note")
async def create_note(body: CreateNoteBody) -> NoteResponse:
    note = create_use_case.execute(CreateNoteInput(body.title, body.body))
    return NoteResponse(id=note.id, title=note.title, body=note.body)
```

Le handler est pur *parse → use-case → response* : il ne porte aucune règle de domaine. Les
vérifications de longueur et de non-vide vivent dans `CreateNoteInput` (ci-dessous), de sorte
qu'elles s'appliquent quelle que soit la surface appelante.

**MCP** — [`src/example/mcp.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/mcp.py) :

```python
@server.tool("Create a new note.")
def create_note(title: str, body: str) -> dict:
    return asdict(note_create.execute(CreateNoteInput(title=title, body=body)))
```

Même `CreateNoteUseCase`, même `CreateNoteInput`, même repository — seule la **surface** diffère.
Les DTOs `Input`/`Output` du UseCase *sont* le contrat pour les deux surfaces ; FastMCP dérive
le schéma de l'outil depuis la signature de la fonction, FastAPI dérive le schéma OpenAPI depuis
le corps Pydantic et le `response_model`.

## Ce que cela vous apporte

- Écrire et tester le domaine **une seule fois** ; le délivrer aux applications (HTTP) et aux
  agents (MCP) depuis le même chemin de code.
- Un bug corrigé dans le UseCase est corrigé sur **les deux** surfaces simultanément.
- Les nouveaux domaines sont accessibles aux agents dès que leurs UseCases existent — `mcp.py`
  câble 15 outils (Note / Tag / Comment) sans plomberie supplémentaire.

## Preuve (un test, pas une affirmation)

[`tests/example/test_http_mcp_parity.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/tests/example/test_http_mcp_parity.py)
câble une application HTTP et un serveur MCP sur le **même** store SQLite et vérifie que les
surfaces sont interchangeables :

- une note créée via l'outil MCP `create_note` est lisible via `GET /examples/notes/{id}`,
- une note créée via HTTP `POST /examples/notes` est lisible via l'outil MCP `get_note`,
- les deux écritures atterrissent dans un même store.

Cela protège le différenciateur sous forme de test de régression — si les deux surfaces divergent
jamais, la CI échoue.

## Ce qui est partagé, et ce qui ne l'est pas

La ligne de démarcation est **règle de domaine vs. mécanique de transport**. Tout ce qui doit
être vrai d'une note, quelle que soit la manière dont elle est arrivée, vit dans le DTO
d'entrée du UseCase et est donc appliqué sur les deux surfaces ; la plomberie de protocole
reste à la frontière.

| Préoccupation | Où elle vit | Partagée avec MCP ? |
|---|---|---|
| Limites de longueur (`max_length`), non-vide | `CreateNoteInput.__post_init__` dans `use_case.py` | **Oui** |
| Logique de création / lecture / mise à jour / suppression, sémantique "non trouvé" | UseCase + entité | **Oui** |
| Parsing de la requête, forme/types des arguments | Corps Pydantic (HTTP) / signature FastMCP (MCP) | Propre à chaque surface |
| Authentification, CORS, throttling | middleware dans `app.py` | Non |
| Parsing de la pagination, formatage d'erreur RFC 9457 | Couche HTTP | Non |

Le `CreateNoteBody` HTTP reflète `max_length` via la même constante `MAX_NOTE_TITLE_LENGTH` —
la limite est donc déclarée une seule fois, documentée dans OpenAPI, *et* appliquée dans le domaine
pour le chemin MCP.

C'est le principe **API-first / couche HTTP fine** en action : la frontière adapte chaque protocole,
le centre tient le domaine. La règle pratique pour les implémenteurs :

> Si une règle doit s'appliquer aux **deux** surfaces, mettez-la dans le UseCase ou l'entité —
> pas dans le handler. Une vérification qui ne vit que dans le handler HTTP ne **protège pas**
> l'outil MCP. (C'est précisément pourquoi les vérifications de longueur et de non-vide ont été
> déplacées dans les DTOs d'entrée — voir les tests de parité.)

## Voir aussi

- [Philosophie de conception → LLM Delivery Ready](design-philosophy.md)
- [Vue d'ensemble de l'architecture](architecture.md)
- [ADR 0011 — MCP comme dépendance centrale](../adr/0011-mcp-as-core-dependency.md)
- [Comment configurer le serveur MCP](../howto/mcp-setup.md)
