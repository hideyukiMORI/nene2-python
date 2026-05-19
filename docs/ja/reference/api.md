# REST API リファレンス

nene2-python example アプリが提供するエンドポイントの一覧です。

> OpenAPI スキーマ（機械可読）は `uv run export-openapi` で `docs/openapi.yaml` に生成できます。
> 開発サーバー起動後は `http://localhost:8080/docs` で Swagger UI を参照できます。

---

## Notes

### `GET /notes`

ノート一覧を取得します。

**クエリパラメータ**

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `limit` | int | 20 | 最大取得件数（上限 100） |
| `offset` | int | 0 | スキップ件数 |

**レスポンス** `200 OK`

```json
{
  "items": [{"id": 1, "title": "ノートタイトル", "body": "本文"}],
  "limit": 20,
  "offset": 0,
  "total": 1
}
```

### `POST /notes`

ノートを作成します。

**リクエストボディ**

```json
{"title": "タイトル", "body": "本文"}
```

**レスポンス** `201 Created`

```json
{"id": 1, "title": "タイトル", "body": "本文"}
```

### `GET /notes/{note_id}`

指定した ID のノートを取得します。存在しない場合は `404` を返します。

### `PUT /notes/{note_id}`

ノートを更新します。

**リクエストボディ**

```json
{"title": "新タイトル", "body": "新本文"}
```

**レスポンス** `200 OK` / `404 Not Found`

### `DELETE /notes/{note_id}`

ノートを削除します。`204 No Content` / `404 Not Found` を返します。

---

## Tags

`/tags` エンドポイントは Notes と同じ CRUD パターンです。

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/tags` | タグ一覧 |
| `POST` | `/tags` | タグ作成（`{"name": "..."}`) |
| `GET` | `/tags/{tag_id}` | タグ取得 |
| `PUT` | `/tags/{tag_id}` | タグ更新（`{"name": "..."}`) |
| `DELETE` | `/tags/{tag_id}` | タグ削除 |

---

## Comments

コメントはノートに紐づくネストリソースです。

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/notes/{note_id}/comments` | コメント一覧 |
| `POST` | `/notes/{note_id}/comments` | コメント作成（`{"body": "..."}`) |
| `GET` | `/notes/{note_id}/comments/{comment_id}` | コメント取得 |
| `PUT` | `/notes/{note_id}/comments/{comment_id}` | コメント更新 |
| `DELETE` | `/notes/{note_id}/comments/{comment_id}` | コメント削除 |

---

## Health Check

### `GET /health`

アプリケーションの稼働状態を返します。

**レスポンス** `200 OK`

```json
{"status": "ok", "db": "ok"}
```

DB 接続失敗時は `db` フィールドが `"error"` になります。

---

## エラーレスポンス

すべてのエラーは RFC 9457 Problem Details 形式で返します。

```json
{
  "type": "https://nene2.dev/problems/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Note with ID 42 was not found."
}
```

| ステータス | type | 原因 |
|---|---|---|
| 400 | `bad-request` | 不正なリクエスト |
| 401 | `unauthorized` | 認証失敗 |
| 404 | `not-found` | リソースが存在しない |
| 413 | `payload-too-large` | ペイロードサイズ超過 |
| 422 | `validation-failed` | バリデーションエラー |
| 429 | `too-many-requests` | レートリミット超過 |
| 500 | `internal-server-error` | サーバー内部エラー |
