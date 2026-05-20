# Field Trial 102: response_model と PaginationResponse の型整合性

## テーマ

`response_model` と `PaginationResponse` / `JSONResponse` の組み合わせパターンを実際に動かして、OpenAPI スキーマへの影響と型整合性を検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft102-response-model/` に 4 パターンを実装:

1. **v1**: `response_model` なし + `JSONResponse` + `PaginationResponse`
2. **v2**: `response_model=ProductListResponse` + Pydantic モデル直返し
3. **v3**: `response_model=ProductListResponse` + `dict` 返却（FastAPI が変換）
4. **v4**: `response_model=ProductListResponse` + `JSONResponse`（検証はされない）

## テスト結果

全 9 テスト通過。

## Friction Points

摩擦なし。

`response-patterns.md` How-to（PR #403 で追加済み）がこのパターンを説明しており、スムーズに実装できた。

- パターン1（JSONResponse + PaginationResponse）は OpenAPI スキーマなしで OK
- パターン2（Pydantic 直返し + response_model）は OpenAPI スキーマあり
- パターン4（JSONResponse + response_model）は response_model があってもバリデーション非実施

前回の摩擦（`problem_details_response()` と Pydantic 直返しの非一貫性）は PR #403 で文書化済み。

## まとめ

ドキュメント整備が功を奏し、摩擦ゼロで実装完了。
