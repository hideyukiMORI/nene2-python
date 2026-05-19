# REST API reference

Endpoints provided by the nene2-python example application.

> Machine-readable schema: run `uv run export-openapi` to generate `docs/openapi.yaml`.  
> Interactive docs: start the dev server and open `http://localhost:8080/docs`.

---

## Notes

### `GET /notes`

List notes with pagination.

**Query parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | int | 20 | Maximum results (max 100) |
| `offset` | int | 0 | Number of results to skip |

**Response** `200 OK`

```json
{
  "items": [{"id": 1, "title": "My note", "body": "Content"}],
  "limit": 20,
  "offset": 0,
  "total": 1
}
```

### `POST /notes`

Create a note.

**Request body**

```json
{"title": "Title", "body": "Body text"}
```

**Response** `201 Created`

```json
{"id": 1, "title": "Title", "body": "Body text"}
```

### `GET /notes/{note_id}`

Get a single note. Returns `404` if not found.

### `PUT /notes/{note_id}`

Update a note.

**Request body**

```json
{"title": "New title", "body": "New body"}
```

**Response** `200 OK` / `404 Not Found`

### `DELETE /notes/{note_id}`

Delete a note. Returns `204 No Content` / `404 Not Found`.

---

## Tags

`/tags` follows the same CRUD pattern as Notes.

| Method | Path | Description |
|---|---|---|
| `GET` | `/tags` | List tags |
| `POST` | `/tags` | Create tag (`{"name": "..."}`) |
| `GET` | `/tags/{tag_id}` | Get tag |
| `PUT` | `/tags/{tag_id}` | Update tag (`{"name": "..."}`) |
| `DELETE` | `/tags/{tag_id}` | Delete tag |

---

## Comments

Comments are nested under a Note.

| Method | Path | Description |
|---|---|---|
| `GET` | `/notes/{note_id}/comments` | List comments |
| `POST` | `/notes/{note_id}/comments` | Create comment (`{"body": "..."}`) |
| `GET` | `/notes/{note_id}/comments/{comment_id}` | Get comment |
| `PUT` | `/notes/{note_id}/comments/{comment_id}` | Update comment |
| `DELETE` | `/notes/{note_id}/comments/{comment_id}` | Delete comment |

---

## Health

### `GET /health`

Returns application health status.

**Response** `200 OK`

```json
{"status": "ok", "db": "ok"}
```

`db` is `"error"` when the database connection fails.

---

## Error responses

All errors use [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457) format.

```json
{
  "type": "https://nene2.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Note with ID 42 was not found."
}
```

| Status | type | Cause |
|---|---|---|
| 400 | `bad-request` | Malformed request |
| 401 | `unauthorized` | Authentication failure |
| 404 | `not-found` | Resource does not exist |
| 413 | `payload-too-large` | Body exceeds size limit |
| 422 | `validation-failed` | Input validation error |
| 429 | `too-many-requests` | Rate limit exceeded |
| 500 | `internal-server-error` | Unhandled server error |
