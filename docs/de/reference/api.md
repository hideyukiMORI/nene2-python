# REST-API-Referenz

Endpunkte der nene2-python-Beispielanwendung.

> Maschinenlesbares Schema: Führen Sie `uv run python src/scripts/export_openapi.py` aus, um `docs/openapi.yaml` zu generieren.  
> Interaktive Dokumentation: Starten Sie den Entwicklungsserver und öffnen Sie `http://localhost:8080/docs`.

---

## Notes

### `GET /notes`

Notizen mit Paginierung auflisten.

**Query-Parameter**

| Parameter | Typ | Standard | Beschreibung |
|---|---|---|---|
| `limit` | int | 20 | Maximale Ergebnisse (max. 100) |
| `offset` | int | 0 | Anzahl der zu überspringenden Ergebnisse |

**Antwort** `200 OK`

```json
{
  "items": [{"id": 1, "title": "My note", "body": "Content"}],
  "limit": 20,
  "offset": 0,
  "total": 1
}
```

### `POST /notes`

Eine Notiz erstellen.

**Request-Body**

```json
{"title": "Title", "body": "Body text"}
```

**Antwort** `201 Created`

```json
{"id": 1, "title": "Title", "body": "Body text"}
```

### `GET /notes/{note_id}`

Eine einzelne Notiz abrufen. Gibt `404` zurück, wenn nicht gefunden.

### `PUT /notes/{note_id}`

Eine Notiz aktualisieren.

**Request-Body**

```json
{"title": "New title", "body": "New body"}
```

**Antwort** `200 OK` / `404 Not Found`

### `DELETE /notes/{note_id}`

Eine Notiz löschen. Gibt `204 No Content` / `404 Not Found` zurück.

---

## Tags

`/tags` folgt demselben CRUD-Muster wie Notes.

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/tags` | Tags auflisten |
| `POST` | `/tags` | Tag erstellen (`{"name": "..."}`) |
| `GET` | `/tags/{tag_id}` | Tag abrufen |
| `PUT` | `/tags/{tag_id}` | Tag aktualisieren (`{"name": "..."}`) |
| `DELETE` | `/tags/{tag_id}` | Tag löschen |

---

## Comments

Kommentare sind unter einer Notiz verschachtelt.

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/notes/{note_id}/comments` | Kommentare auflisten |
| `POST` | `/notes/{note_id}/comments` | Kommentar erstellen (`{"body": "..."}`) |
| `GET` | `/notes/{note_id}/comments/{comment_id}` | Kommentar abrufen |
| `PUT` | `/notes/{note_id}/comments/{comment_id}` | Kommentar aktualisieren |
| `DELETE` | `/notes/{note_id}/comments/{comment_id}` | Kommentar löschen |

---

## Health

### `GET /health`

Gibt den Anwendungs-Gesundheitsstatus zurück.

**Antwort** `200 OK`

```json
{"status": "ok", "db": "ok"}
```

`db` ist `"error"`, wenn die Datenbankverbindung fehlschlägt.

---

## Fehlerantworten

Alle Fehler verwenden das Format [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457).

```json
{
  "type": "https://nene2.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Note with ID 42 was not found."
}
```

| Status | type | Ursache |
|---|---|---|
| 400 | `bad-request` | Fehlerhafte Anfrage |
| 401 | `unauthorized` | Authentifizierungsfehler |
| 404 | `not-found` | Ressource existiert nicht |
| 413 | `payload-too-large` | Body überschreitet Größenlimit |
| 422 | `validation-failed` | Eingabevalidierungsfehler |
| 429 | `too-many-requests` | Rate-Limit überschritten |
| 500 | `internal-server-error` | Unbehandelter Serverfehler |
