# Référence de l'API REST

Endpoints fournis par l'application exemple nene2-python.

> Schéma lisible par machine : exécutez `uv run python src/scripts/export_openapi.py` pour générer `docs/openapi.yaml`.  
> Documentation interactive : démarrez le serveur de développement et ouvrez `http://localhost:8080/docs`.

---

## Notes

### `GET /notes`

Lister les notes avec pagination.

**Paramètres de requête**

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `limit` | int | 20 | Résultats maximum (max 100) |
| `offset` | int | 0 | Nombre de résultats à ignorer |

**Réponse** `200 OK`

```json
{
  "items": [{"id": 1, "title": "Ma note", "body": "Contenu"}],
  "limit": 20,
  "offset": 0,
  "total": 1
}
```

### `POST /notes`

Créer une note.

**Corps de la requête**

```json
{"title": "Titre", "body": "Texte du corps"}
```

**Réponse** `201 Created`

```json
{"id": 1, "title": "Titre", "body": "Texte du corps"}
```

### `GET /notes/{note_id}`

Obtenir une seule note. Retourne `404` si non trouvée.

### `PUT /notes/{note_id}`

Modifier une note.

**Corps de la requête**

```json
{"title": "Nouveau titre", "body": "Nouveau corps"}
```

**Réponse** `200 OK` / `404 Not Found`

### `DELETE /notes/{note_id}`

Supprimer une note. Retourne `204 No Content` / `404 Not Found`.

---

## Tags

`/tags` suit le même schéma CRUD que les Notes.

| Méthode | Chemin | Description |
|---|---|---|
| `GET` | `/tags` | Lister les tags |
| `POST` | `/tags` | Créer un tag (`{"name": "..."}`) |
| `GET` | `/tags/{tag_id}` | Obtenir un tag |
| `PUT` | `/tags/{tag_id}` | Modifier un tag (`{"name": "..."}`) |
| `DELETE` | `/tags/{tag_id}` | Supprimer un tag |

---

## Commentaires

Les commentaires sont imbriqués sous une Note.

| Méthode | Chemin | Description |
|---|---|---|
| `GET` | `/notes/{note_id}/comments` | Lister les commentaires |
| `POST` | `/notes/{note_id}/comments` | Créer un commentaire (`{"body": "..."}`) |
| `GET` | `/notes/{note_id}/comments/{comment_id}` | Obtenir un commentaire |
| `PUT` | `/notes/{note_id}/comments/{comment_id}` | Modifier un commentaire |
| `DELETE` | `/notes/{note_id}/comments/{comment_id}` | Supprimer un commentaire |

---

## Santé

### `GET /health`

Retourne l'état de santé de l'application.

**Réponse** `200 OK`

```json
{"status": "ok", "db": "ok"}
```

`db` vaut `"error"` quand la connexion à la base de données échoue.

---

## Réponses d'erreur

Toutes les erreurs utilisent le format [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457).

```json
{
  "type": "https://nene2.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Note with ID 42 was not found."
}
```

| Statut | type | Cause |
|---|---|---|
| 400 | `bad-request` | Requête malformée |
| 401 | `unauthorized` | Échec d'authentification |
| 404 | `not-found` | La ressource n'existe pas |
| 413 | `payload-too-large` | Corps dépasse la limite de taille |
| 422 | `validation-failed` | Erreur de validation des entrées |
| 429 | `too-many-requests` | Limite de débit dépassée |
| 500 | `internal-server-error` | Erreur serveur non gérée |
