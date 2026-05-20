# FT87: カスタムレスポンスヘッダー — X-Total-Count / X-RateLimit パターン検証

**日付**: 2026-05-20  
**テーマ**: JSONResponse へのカスタムヘッダー付与と nene2 ユーティリティとの統合  
**バージョン**: v1.8.29  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft87-response-headers/`

---

## 概要

カスタムレスポンスヘッダー（`X-Total-Count`, `X-RateLimit-Remaining`, etc.）の付与パターンを
4種類検証した。JSONResponse コンストラクタでの直接指定が最も簡単だが、
`problem_details_response()` に `headers` パラメーターがなく、
エラーレスポンスにヘッダーを付けられない摩擦が発見された。

---

## 4パターンの比較

### パターン1: JSONResponse コンストラクタ（✅ 推奨）

```python
@app.get("/items", response_model=list[ItemResponse])
def list_items(pagination: PaginationDep) -> JSONResponse:
    items, total = ...
    return JSONResponse(
        content={"items": items, "total": total},
        headers={
            "X-Total-Count": str(total),
            "X-Limit": str(pagination.limit),
        },
    )
```

最もシンプル。nene2 スタイルと完全一致。

### パターン2: `response: Response` パラメーター（❌ JSONResponse では無視）

```python
@app.get("/items")
def list_items(response: Response) -> JSONResponse:
    response.headers["X-Total"] = "10"  # ← 無視される
    return JSONResponse({"items": [...]})
```

FastAPI の `response: Response` でのヘッダー設定は、
ハンドラーが `JSONResponse` を直接返す場合は無視される。
`JSONResponse` はそれ自体が完全なレスポンスオブジェクトのため。

### パターン3: ミドルウェアで一括付与

```python
class XServerVersionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Server-Version"] = "1.0"
        return response
```

全レスポンスに共通ヘッダーを付ける場合に有効。
nene2 の `SecurityHeadersMiddleware` と同様のパターン。

### パターン4: PaginationResponse + ヘッダー

```python
pagination_response = PaginationResponse(
    items=data, limit=pagination.limit, offset=pagination.offset, total=total
)
return JSONResponse(
    content=pagination_response.to_dict(),
    headers={"X-Total-Count": str(total), "X-Total-Pages": str(total_pages)},
)
```

---

## 発見した問題

### 問題1: `problem_details_response()` に `headers` パラメーターがない

```python
# やりたいこと: 429 レスポンスに Retry-After ヘッダーを付ける
return problem_details_response(
    "rate-limited", "Rate Limited", 429, "Too many requests.",
    headers={"Retry-After": "60", "X-RateLimit-Remaining": "0"},  # ← パラメーターが存在しない
)

# 現状の回避策（冗長）:
body = {
    "type": "https://nene2.dev/problems/rate-limited",
    "title": "Rate Limited",
    "status": 429,
    "detail": "Too many requests.",
}
return JSONResponse(content=body, status_code=429,
                   media_type="application/problem+json",
                   headers={"Retry-After": "60"})
```

RFC 7807 / 9457 では `Retry-After`, `WWW-Authenticate`, `Location` などのヘッダーが
エラーレスポンスに必要なケースが多い。現在は `problem_details_response()` を捨てて
`JSONResponse` を直接構築する必要がある。

### 問題2: `response: Response` パラメーターが JSONResponse と非一貫

```python
# FastAPI ドキュメントには response: Response でヘッダーを設定する方法が書かれているが、
# JSONResponse を直接返す nene2 スタイルでは動作しない
@app.get("/items")
def list_items(response: Response) -> JSONResponse:
    response.headers["X-Total"] = "10"  # ← 無視される ← 摩擦
    return JSONResponse({"items": []})
```

FastAPI ドキュメントを読んだユーザーが試みるパターンだが、
nene2 の JSONResponse スタイルでは動作しない。

### 問題3: PaginationResponse に `page` / `total_pages` がない

```python
# ユーザーが期待するインターフェース（page-based）
PaginationResponse(items=data, total=100, page=2, per_page=20)
# → total_pages = 5 を自動計算してほしい

# 実際のインターフェース（offset-based）
PaginationResponse(items=data, limit=20, offset=20, total=100)
# → page や total_pages は自分で計算する必要がある
```

`page` / `total_pages` を使いたい場合は手動計算が必要。
Frontend に `X-Total-Pages` ヘッダーを返したいケースで毎回計算コードが必要になる。

---

## テスト結果（全11件パス）

```
test_list_returns_x_total_count_header                     PASSED
test_list_returns_pagination_headers                       PASSED
test_create_returns_x_resource_id_header                   PASSED
test_get_item_returns_version_header                       PASSED
test_404_does_not_have_version_header                      PASSED
test_nene2_security_headers_preserved                      PASSED
test_middleware_adds_server_version_to_all_responses       PASSED
test_pagination_headers_match_body                         PASSED
test_pagination_header_limit_value                         PASSED
test_friction_response_param_ignored_with_json_response    PASSED
test_friction_problem_details_response_no_custom_headers   PASSED
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F87-1 | `problem_details_response()` に `headers` パラメーターがない — エラーレスポンスへのヘッダー付与が不便 | 高 |
| F87-2 | `response: Response` パラメーターのヘッダー設定が JSONResponse では無視される（未文書） | 中 |
| F87-3 | `PaginationResponse` に `page` / `total_pages` がなく手動計算が必要 | 低 |

---

## 使用感（主観評価）

### 直感性 ★★★★☆

JSONResponse コンストラクタへの直接指定は直感的でシンプル。
問題は `problem_details_response()` でエラーヘッダーが付けられないこと。

### 実害の深刻さ ★★★★☆

429 Rate Limited + `Retry-After` ヘッダーは RFC 6585 で推奨されている組み合わせ。
現状では `problem_details_response()` が使えず、
RFC 9457 フォーマットと一致した手動 JSONResponse 構築が必要になる。

### 修正のしやすさ ★★★★★

`problem_details_response()` に `headers: dict[str, str] | None = None` を追加するだけ。
変更は最小で後方互換性あり。

### 総合コメント

F87-1 はコード修正で簡単に解決できる高影響の摩擦点。
`problem_details_response()` を nene2 のメインの エラー応答ファクトリとして機能させるなら、
`headers` パラメーターは必須機能と言える。

---

## 推奨アクション

1. **fix**: `problem_details_response()` に `headers: dict[str, str] | None = None` パラメーターを追加
2. **docs**: `response: Response` パラメーターが JSONResponse と非互換であることを how-to に明記
3. **docs**: カスタムレスポンスヘッダーの推奨パターンを how-to に追加
