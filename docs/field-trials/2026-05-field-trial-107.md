# Field Trial 107: Bulk Operations（一括作成・削除）

## テーマ

`POST /items/bulk` と `DELETE /items/bulk` による一括操作パターンを検証する。
部分成功（一部成功・一部失敗）を 207 Multi-Status で返す方法も確認する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft107-bulk-ops/` に以下を実装:

- `POST /items/bulk` — 一括作成（価格制限でビジネスバリデーション、部分失敗対応）
- `DELETE /items/bulk` — 一括削除（存在しない ID は failed に入れる）
- 207 Multi-Status レスポンスに `succeeded` / `failed` を含める
- 8 テスト通過（修正後）

## テスト結果

全 8 テスト通過（修正後）。

## Friction Points

### FP1: `TestClient.delete()` が `json` パラメーターを受け付けない

**状況**: `DELETE` リクエストにリクエストボディを付ける場合、`client.delete(url, json=body)` は `TypeError` になる。

```python
# ❌ TypeError: unexpected keyword argument 'json'
r = client.delete("/items/bulk", json={"ids": [1, 2]})

# ✅ request() を使う
r = client.request("DELETE", "/items/bulk", json={"ids": [1, 2]})
```

**影響**: 中。DELETE + ボディはやや非標準だが、一括削除では一般的なパターン。テストコードが `request()` を直接使う必要があるため直感的でない。

**代替案**: ボディを持つ DELETE の代わりに `POST /items/bulk-delete` にする方が REST 的にクリーン（ボディを持つ DELETE は RFC 9110 で「意味がないわけではないが、推奨されない」）。

### FP2: 207 Multi-Status のレスポンス型が OpenAPI スキーマに表現しにくい

**状況**: `response_model` で 207 のスキーマを定義しようとすると、succeeded/failed の型が複雑になる。実用的には `response_model` なしで `JSONResponse` を直接返すのが現実的。

## まとめ

FP1 は how-to に追記（`TestClient` の HTTP メソッドと `json` パラメーターの注意点）。
FP2 はドキュメント摩擦（bulk 操作は `response_model` を省略して OK）。
