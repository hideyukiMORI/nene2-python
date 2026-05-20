# Field Trial 97: HTTP キャッシュヘッダー (ETag / Cache-Control)

**日付**: 2026-05-20
**テーマ**: ETag・Cache-Control・304 Not Modified パターンを nene2 で実装
**バージョン**: v1.8.30
**結果**: 摩擦あり（コード修正なし）

---

## 目的

HTTP キャッシュ機構（`ETag`, `Cache-Control`, `If-None-Match`, `304 Not Modified`）を nene2 ベースの API で実装するパターンを検証する。

---

## 実施内容

`/home/xi/docker/nene2-python-FT/ft97-http-caching/` に以下を実装:

- `app.py` — ETag 付き GET エンドポイント、`If-None-Match` による 304 返却、Cache-Control ヘッダー
- 13 テスト（全 PASS）

---

## 確認できた良好な動作

### ETag + 304 のパターン

`If-None-Match` ヘッダーと ETag を比較して 304 を返すパターンは問題なく動作する。

```python
@app.get("/articles/{article_id}")
def get_article(article_id: int, request: Request) -> Response:
    data = _article_to_dict(article)
    etag = _compute_etag(data)

    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})

    return JSONResponse(data, headers={"ETag": etag, "Cache-Control": "max-age=60"})
```

### 304 レスポンスにも X-Request-Id が付く

`Response(status_code=304)` を返しても、外側の `RequestIdMiddleware` が `X-Request-Id` を付与する。

---

## 摩擦点

### F97-1: nene2 に ETag 生成ユーティリティがない

ETag 生成ロジック（MD5 ハッシュ）を各プロジェクトで手動実装する必要がある。各エンドポイントで繰り返し実装することになり DRY でない。

```python
def _compute_etag(data: object) -> str:
    content = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return f'"{hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()}"'
```

nene2 が `generate_etag(data)` などのユーティリティ関数を提供すれば再実装不要になる。

### F97-2: `hashlib.md5()` に `usedforsecurity=False` が必要

ruff のセキュリティルール `S324`（MD5 使用禁止）により、ETag 生成で `hashlib.md5()` を使うと lint エラーになる。ETag は暗号セキュリティ用途ではないが、明示的に `usedforsecurity=False` を指定する必要がある。

```python
# ❌ ruff S324 エラー
hashlib.md5(content.encode()).hexdigest()

# ✅ 正しい
hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()
```

nene2 のユーティリティ関数でラップすればプロジェクトごとに対処不要になる。

### F97-3: Cache-Control ヘッダーの付与はエンドポイントごとに手動

`JSONResponse(headers={"Cache-Control": "max-age=60"})` のように各エンドポイントで手動指定が必要。
ミドルウェアでのデフォルト付与（例: 全 GET に `Cache-Control: no-cache` を付与する設定）がないため、付け忘れが起きやすい。

---

## 結論

HTTP キャッシュヘッダーは nene2 と問題なく実装できるが、ETag 生成の共通化がない。
`generate_etag()` などのユーティリティ関数を nene2 に追加することで摩擦を解消できる。
