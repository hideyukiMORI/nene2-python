# Field Trial 96: カスタム例外ハンドラーと nene2 ErrorHandlerMiddleware の共存

**日付**: 2026-05-20
**テーマ**: `app.exception_handler()` と `ErrorHandlerMiddleware` の優先順位・共存パターン
**バージョン**: v1.8.30
**結果**: 摩擦あり（コード修正なし）

---

## 目的

FastAPI の `app.exception_handler()` を使ってドメイン固有の例外を HTTP レスポンスに変換するパターンを検証する。nene2 の `ErrorHandlerMiddleware` との共存時の優先順位と挙動を確認する。

---

## 実施内容

`/home/xi/docker/nene2-python-FT/ft96-exception-handlers/` に以下を実装:

- `app.py` — `ItemNotFoundError`, `InsufficientStockError`, `ForbiddenOperationError` + カスタムハンドラー
- 15 テスト（全 PASS）

---

## 確認できた良好な動作

### ドメイン例外 → Problem Details の変換

`@app.exception_handler(DomainError)` 内で `problem_details_response()` を使うと、ドメイン例外を RFC 9457 形式で返せる。

```python
@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError) -> JSONResponse:
    return problem_details_response(
        "item-not-found", "Item Not Found", 404,
        f"Item with ID {exc.item_id} does not exist.",
    )
```

### カスタムハンドラーのレスポンスにもミドルウェアが適用される

`app.exception_handler()` で返したレスポンスにも、外側のミドルウェア（`RequestIdMiddleware`, `SecurityHeadersMiddleware`）が適用されるため、`X-Request-Id` とセキュリティヘッダーが付与される。

---

## 摩擦点

### F96-1: `problem_details_response()` の `extra` はトップレベルに展開される

`extra={"item_id": 1, "available": 0}` を渡すと、`errors` キーの下ではなく **レスポンスボディのトップレベル** に展開される。

```json
// extra={"item_id": 2, "available": 0} を渡した場合
{
  "type": "https://nene2.dev/problems/insufficient-stock",
  "title": "Insufficient Stock",
  "status": 409,
  "detail": "...",
  "item_id": 2,    // ← トップレベルに展開
  "available": 0   // ← トップレベルに展開
}
```

テストで `data["extra"]["available"]` とアクセスすると `KeyError` になる。正しくは `data["available"]`。RFC 9457 ではトップレベル展開が仕様に沿っている（拡張メンバーはトップレベルに置く）が、初見では迷いやすい。

### F96-2: `HTTPException` は FastAPI が処理するため `application/problem+json` にならない

`raise StarletteHTTPException(status_code=418, detail="...")` を発生させると、FastAPI の内部 `ExceptionMiddleware` が処理する。この時点で nene2 の `ErrorHandlerMiddleware` には到達せず、レスポンスの `Content-Type` は `application/json` のまま（`application/problem+json` にはならない）。

```python
# ❌ HTTPException は ErrorHandlerMiddleware を通らない
raise HTTPException(status_code=404, detail="Not found")
# → Content-Type: application/json（Problem Details 形式ではない）

# ✅ ドメイン例外 + exception_handler を使う
raise ItemNotFoundError(item_id)
# → Content-Type: application/problem+json
```

すべてのエラーを Problem Details で統一したい場合は、`HTTPException` を直接 raise するのを避け、ドメイン例外 + カスタムハンドラーのパターンで統一する。または `app.exception_handler(HTTPException)` でオーバーライドする。

### F96-3: カスタム例外ハンドラーと `ErrorHandlerMiddleware` の処理レイヤーの違い

| 処理 | レイヤー | タイミング |
|---|---|---|
| `app.exception_handler()` | Starlette ExceptionMiddleware | FastAPI ルーティング後 |
| `ErrorHandlerMiddleware` | BaseHTTPMiddleware | ExceptionMiddleware の外側 |

カスタムハンドラーで処理されたレスポンスには `ErrorHandlerMiddleware` が適用されないが、さらに外側の `RequestIdMiddleware` / `SecurityHeadersMiddleware` は適用される。

---

## 結論

`app.exception_handler()` + `problem_details_response()` は nene2 と問題なく組み合わせられる。
主な摩擦は `extra` のトップレベル展開の把握と、`HTTPException` が Problem Details にならない点。
`HTTPException` を使わずドメイン例外で統一するパターンが推奨。コード修正は不要。
