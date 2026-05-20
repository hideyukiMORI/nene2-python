# Field Trial 94: ミドルウェア順序とエラーレスポンスのヘッダー

**日付**: 2026-05-20
**テーマ**: `setup_middlewares()` のスタックで、エラー時にもヘッダーが付くことの検証
**バージョン**: v1.8.30
**結果**: 摩擦あり（コード修正なし）

---

## 目的

`setup_middlewares()` が生成するミドルウェアスタックで、各種エラーレスポンス（404 / 500 / 422）においても `X-Request-Id` やセキュリティヘッダーが正しく付与されることを検証する。

---

## 実施内容

`/home/xi/docker/nene2-python-FT/ft94-middleware-error-headers/` に以下を実装:

- `app.py` — 正常・404・500・422 を返すエンドポイント
- 14 テスト（全 PASS）

---

## 確認できた良好な動作

`setup_middlewares()` を使うと、以下すべてのケースで `X-Request-Id` とセキュリティヘッダーが付与される:

| シナリオ | X-Request-Id | Security Headers | Content-Type |
|---|---|---|---|
| 200 正常 | ✅ | ✅ | `application/json` |
| 404 Problem Details | ✅ | ✅ | `application/problem+json` |
| 500 例外キャッチ | ✅ | ✅ | `application/problem+json` |
| 422 バリデーション | ✅ | ✅ | `application/problem+json` |
| FastAPI 自動生成 404 | ✅ | ✅ | `application/problem+json` |

`ErrorHandlerMiddleware` が内側で例外を捕捉して新しい Response を生成しても、外側の `RequestIdMiddleware` と `SecurityHeadersMiddleware` が正しくヘッダーを付与する。

---

## 摩擦点

### F94-1: `SecurityHeadersMiddleware` は `X-XSS-Protection` を付与しない

`X-XSS-Protection` は古い（現代のブラウザでは不要）ため、nene2 の `SecurityHeadersMiddleware` は付与しない。実際に付与されるセキュリティヘッダー:

```
x-content-type-options: nosniff
x-frame-options: DENY
referrer-policy: strict-origin-when-cross-origin
permissions-policy: geolocation=(), microphone=()
content-security-policy: default-src 'self'
```

`X-XSS-Protection` の付与を期待したテストは失敗する。ドキュメントで付与ヘッダーを明記する必要がある。

### F94-2: `ThrottleMiddleware` は同一テストプロセス内でリクエスト数を累積する

`setup_middlewares(app, throttle_limit=10)` で ThrottleMiddleware を有効にすると、各テストで作成した `TestClient` が共有するカウンターが累積し、後続テストが 429 を返す。

```python
# ❌ throttle_limit=10 を指定すると 10 リクエスト後に 429
setup_middlewares(app, throttle_limit=10)
# テスト14個 × 各1リクエスト = 14リクエスト → 途中から 429 になる

# ✅ ThrottleMiddleware のテストには専用の app インスタンスを使う
app_throttle = FastAPI()
setup_middlewares(app_throttle, throttle_limit=3)
```

ThrottleMiddleware の動作をテストする場合は、専用の `FastAPI()` インスタンスを作成するか、テストごとにカウンターをリセットする仕組みが必要。

### F94-3: `ErrorHandlerMiddleware` が新しい Response を返すと内側ミドルウェアをバイパスする

Starlette の `BaseHTTPMiddleware` の仕様として、内側のミドルウェアが例外をキャッチして新しい `Response` を返す際、さらに内側のミドルウェアはバイパスされる。

`setup_middlewares()` は `RequestIdMiddleware` を最外側、`ErrorHandlerMiddleware` を最内側に置くことで、エラー時もヘッダーが付くことを保証している。自前で `add_middleware` を呼ぶ場合はこの順序を守る必要がある。

```python
# setup_middlewares() が保証する順序（内側→外側）
ErrorHandlerMiddleware → RequestLoggingMiddleware → ThrottleMiddleware
→ RequestSizeLimitMiddleware → SecurityHeadersMiddleware → RequestIdMiddleware
```

---

## 結論

`setup_middlewares()` を使えばエラー時のヘッダー付与は保証される。
主な摩擦は `SecurityHeadersMiddleware` が付与するヘッダーの正確な把握と、ThrottleMiddleware のテスト時の累積カウンター問題。
コード修正は不要で、ドキュメントの整備で対応できる。
