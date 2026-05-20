# Field Trial 108: Pydantic computed_field と property パターン

## テーマ

Pydantic v2 の `@computed_field` + `@property` を使って、ストアドフィールドから計算されるプロパティを
OpenAPI スキーマに自動的に含めるパターンを検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft108-computed-field/` に以下を実装:

- `ProductResponse` — `price_dollars`, `is_in_stock`, `display_name` の computed fields
- `OrderLineResponse` — ネストした computed fields (`line_total_cents`, `line_total_dollars`)
- `/order-preview` エンドポイントで `JSONResponse(line.model_dump(mode="json"))` パターン確認
- 6 テスト通過

## テスト結果

全 6 テスト通過。

## Friction Points

### FP1: `model_dump()` が datetime を Python オブジェクトのまま返す → `JSONResponse` で 500 エラー

**状況**: `OrderLineResponse` のネストモデルには `created_at: datetime` フィールドがある。
`JSONResponse(line.model_dump())` を使うと、`json.dumps` が `datetime` を直列化できずに
`TypeError: Object of type datetime is not JSON serializable` で 500 エラーになる。

```python
# ❌ model_dump() は datetime をそのまま返す → JSONResponse でエラー
return JSONResponse(line.model_dump())

# ✅ mode="json" を指定すると datetime を ISO 8601 文字列に変換する
return JSONResponse(line.model_dump(mode="json"))
```

**影響**: 大。`response_model=` を使う通常のルートは FastAPI が自動変換するため問題ないが、
`JSONResponse` を直接返すルート（207 Multi-Status, /order-preview など）でこのパターンを
使い忘れると本番で 500 エラーになる。

**代替案**: `jsonable_encoder(line.model_dump())` でも変換できるが、`mode="json"` の方が Pydantic 標準。

## まとめ

`@computed_field` + `@property` は摩擦ゼロで OpenAPI スキーマに含められる優れたパターン。
FP1 は `JSONResponse` を直接使う場合の注意点として how-to に追記する。
