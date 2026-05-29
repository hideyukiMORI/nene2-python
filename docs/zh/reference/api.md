# REST API 参考

nene2-python 示例应用提供的 endpoint。

> 机器可读 schema：运行 `uv run python src/scripts/export_openapi.py` 生成 `docs/openapi.yaml`。
> 交互式文档：启动开发服务器后打开 `http://localhost:8080/docs`。

---

## Notes

### `GET /notes`

分页获取笔记列表。

**查询参数**

| 参数 | 类型 | 默认值 | 描述 |
|---|---|---|---|
| `limit` | int | 20 | 最大返回数量（最多 100） |
| `offset` | int | 0 | 跳过的数量 |

**响应** `200 OK`

```json
{
  "items": [{"id": 1, "title": "My note", "body": "Content"}],
  "limit": 20,
  "offset": 0,
  "total": 1
}
```

### `POST /notes`

创建笔记。

**请求体**

```json
{"title": "Title", "body": "Body text"}
```

**响应** `201 Created`

```json
{"id": 1, "title": "Title", "body": "Body text"}
```

### `GET /notes/{note_id}`

获取单条笔记。不存在时返回 `404`。

### `PUT /notes/{note_id}`

更新笔记。

**请求体**

```json
{"title": "New title", "body": "New body"}
```

**响应** `200 OK` / `404 Not Found`

### `DELETE /notes/{note_id}`

删除笔记。返回 `204 No Content` / `404 Not Found`。

---

## Tags

`/tags` 遵循与 Notes 相同的 CRUD 模式。

| 方法 | 路径 | 描述 |
|---|---|---|
| `GET` | `/tags` | 获取标签列表 |
| `POST` | `/tags` | 创建标签（`{"name": "..."}`） |
| `GET` | `/tags/{tag_id}` | 获取标签 |
| `PUT` | `/tags/{tag_id}` | 更新标签（`{"name": "..."}`） |
| `DELETE` | `/tags/{tag_id}` | 删除标签 |

---

## Comments

Comments 嵌套在 Note 下。

| 方法 | 路径 | 描述 |
|---|---|---|
| `GET` | `/notes/{note_id}/comments` | 获取评论列表 |
| `POST` | `/notes/{note_id}/comments` | 创建评论（`{"body": "..."}`） |
| `GET` | `/notes/{note_id}/comments/{comment_id}` | 获取评论 |
| `PUT` | `/notes/{note_id}/comments/{comment_id}` | 更新评论 |
| `DELETE` | `/notes/{note_id}/comments/{comment_id}` | 删除评论 |

---

## 健康检查

### `GET /health`

返回应用健康状态。

**响应** `200 OK`

```json
{"status": "ok", "db": "ok"}
```

数据库连接失败时 `db` 为 `"error"`。

---

## 错误响应

所有错误使用 [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457) 格式。

```json
{
  "type": "https://nene2.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Note with ID 42 was not found."
}
```

| 状态码 | type | 原因 |
|---|---|---|
| 400 | `bad-request` | 请求格式错误 |
| 401 | `unauthorized` | 身份验证失败 |
| 404 | `not-found` | 资源不存在 |
| 413 | `payload-too-large` | 请求体超过大小限制 |
| 422 | `validation-failed` | 输入验证错误 |
| 429 | `too-many-requests` | 超过限流限制 |
| 500 | `internal-server-error` | 未处理的服务器错误 |
