# Referência da API REST

Endpoints fornecidos pela aplicação de exemplo do nene2-python.

> Schema legível por máquina: execute `uv run python src/scripts/export_openapi.py` para gerar `docs/openapi.yaml`.  
> Docs interativos: inicie o servidor de desenvolvimento e abra `http://localhost:8080/docs`.

---

## Notes

### `GET /notes`

Lista notas com paginação.

**Parâmetros de query**

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `limit` | int | 20 | Máximo de resultados (máx 100) |
| `offset` | int | 0 | Número de resultados a pular |

**Resposta** `200 OK`

```json
{
  "items": [{"id": 1, "title": "My note", "body": "Content"}],
  "limit": 20,
  "offset": 0,
  "total": 1
}
```

### `POST /notes`

Cria uma nota.

**Corpo da requisição**

```json
{"title": "Title", "body": "Body text"}
```

**Resposta** `201 Created`

```json
{"id": 1, "title": "Title", "body": "Body text"}
```

### `GET /notes/{note_id}`

Busca uma nota específica. Retorna `404` se não encontrada.

### `PUT /notes/{note_id}`

Atualiza uma nota.

**Corpo da requisição**

```json
{"title": "New title", "body": "New body"}
```

**Resposta** `200 OK` / `404 Not Found`

### `DELETE /notes/{note_id}`

Deleta uma nota. Retorna `204 No Content` / `404 Not Found`.

---

## Tags

`/tags` segue o mesmo padrão CRUD que Notes.

| Método | Caminho | Descrição |
|---|---|---|
| `GET` | `/tags` | Listar tags |
| `POST` | `/tags` | Criar tag (`{"name": "..."}`) |
| `GET` | `/tags/{tag_id}` | Buscar tag |
| `PUT` | `/tags/{tag_id}` | Atualizar tag (`{"name": "..."}`) |
| `DELETE` | `/tags/{tag_id}` | Deletar tag |

---

## Comments

Comments são aninhados sob uma Note.

| Método | Caminho | Descrição |
|---|---|---|
| `GET` | `/notes/{note_id}/comments` | Listar comentários |
| `POST` | `/notes/{note_id}/comments` | Criar comentário (`{"body": "..."}`) |
| `GET` | `/notes/{note_id}/comments/{comment_id}` | Buscar comentário |
| `PUT` | `/notes/{note_id}/comments/{comment_id}` | Atualizar comentário |
| `DELETE` | `/notes/{note_id}/comments/{comment_id}` | Deletar comentário |

---

## Health

### `GET /health`

Retorna o status de saúde da aplicação.

**Resposta** `200 OK`

```json
{"status": "ok", "db": "ok"}
```

`db` é `"error"` quando a conexão com o banco de dados falha.

---

## Respostas de erro

Todos os erros usam o formato [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457).

```json
{
  "type": "https://nene2.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Note with ID 42 was not found."
}
```

| Status | type | Causa |
|---|---|---|
| 400 | `bad-request` | Requisição malformada |
| 401 | `unauthorized` | Falha de autenticação |
| 404 | `not-found` | Recurso não existe |
| 413 | `payload-too-large` | Body excede o limite de tamanho |
| 422 | `validation-failed` | Erro de validação de entrada |
| 429 | `too-many-requests` | Limite de rate limit excedido |
| 500 | `internal-server-error` | Erro de servidor não tratado |
