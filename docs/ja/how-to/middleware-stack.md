# How-To: ミドルウェアスタックの正しい設定

## 推奨: `setup_middlewares()` を使う

手動で `add_middleware` を並べる代わりに、フレームワーク提供のヘルパーを使うと
LIFO 順序ミス（500 に `X-Request-Id` が付かない等）を防げる。

```python
from nene2.middleware import setup_middlewares

setup_middlewares(
    app,
    debug=cfg.app_debug,
    domain_handlers=[NoteNotFoundExceptionHandler()],
    throttle_limit=cfg.throttle_limit if cfg.throttle_enabled else None,
    max_request_bytes=cfg.max_body_size,
    cors_allowed_origins=cfg.cors_origins if cfg.cors_enabled else None,
)
```

有効なスタック（外側 → 内側）:

```
CORS → RequestId → SecurityHeaders → SizeLimit → Throttle → RequestLogging → ErrorHandler
```

カスタムミドルウェアが必要な場合のみ、以下の手動登録パターンを使う。

---

## 手動登録（TL;DR）

```python
# この順序で add_middleware を呼ぶ
app.add_middleware(ErrorHandlerMiddleware)           # 最内側
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ThrottleMiddleware, limit=100, window=60)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)              # 最外側
```

---

## なぜこの順序なのか

### Starlette の LIFO ルール

`app.add_middleware()` は **後から追加したものが外側**（LIFO）になる。

```
add_middleware(A)  →  B(A(Router))
add_middleware(B)
```

リクエストは外側から内側へ（B → A → Router）、
レスポンスは内側から外側へ（Router → A → B）流れる。

### ErrorHandler を最外側にすると何が壊れるか

```python
# ❌ 間違い
app.add_middleware(RequestIdMiddleware)
app.add_middleware(ErrorHandlerMiddleware)  # 最外側
# スタック: ErrorHandler(RequestId(Router))
```

ハンドラーが例外を raise したとき:

1. `ErrorHandlerMiddleware.dispatch` が例外を捕捉
2. `problem_details_response(...)` で **新しい Response を直接 return**
3. この Response は内側の `RequestId` ミドルウェアを **通過しない**
4. 結果: **500 エラーに `X-Request-Id` が付かない**

同じ理由で `SecurityHeadersMiddleware` が内側にあると、
エラーレスポンスにセキュリティヘッダーが付かない。

### 正しい順序のスタック図

```
RequestIdMiddleware            ← 全レスポンス（200〜5xx）に X-Request-Id を付与
  └─ SecurityHeadersMiddleware ← 全レスポンスにセキュリティヘッダーを付与
       └─ RequestSizeLimitMiddleware ← 413 を直接返す（ErrorHandler 不要）
            └─ ThrottleMiddleware   ← 429 を直接返す（ErrorHandler 不要）
                 └─ RequestLoggingMiddleware
                      └─ ErrorHandlerMiddleware ← ハンドラー例外を 500 に変換
                           └─ Router (FastAPI handlers)
```

`RequestSizeLimitMiddleware` と `ThrottleMiddleware` は自身で `problem_details_response()` を
返すため、ErrorHandler の内外に置いても 413/429 の形式は変わらない。
ただし `X-Request-Id` が付くかどうかは `RequestIdMiddleware` の位置次第。

---

## 使用しないミドルウェアがある場合

一部のミドルウェアを省略しても、残りの順序は同じルールに従う:

```python
# ThrottleMiddleware と RequestLoggingMiddleware を省略した場合
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
```

---

## ErrorHandlerMiddleware.install() を使う場合

`install()` は `add_middleware` と `add_exception_handler` をまとめて行うが、
他のミドルウェアとの順序設定は手動で行う必要がある:

```python
# install() は最初に呼ぶ（最内側になる）
ErrorHandlerMiddleware.install(app)          # 内側

# その後に他のミドルウェアを追加
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)       # 外側
```

---

## よくある質問

**Q: `RequestSizeLimitMiddleware` は ErrorHandler の内外どちらに置くべきか?**

A: 内外どちらでも機能するが、`RequestIdMiddleware` より内側にすることで
413 レスポンスにも `X-Request-Id` が付く。上記の推奨順序に従えばよい。

**Q: カスタムミドルウェアはどこに追加するか?**

A: そのミドルウェアの性質による:
- 全レスポンスに何かを追加したい → `RequestIdMiddleware` の直前（外側）
- ハンドラー例外をキャッチしたい → `ErrorHandlerMiddleware` の直後（内側）
- リクエストを早期拒否したい → `RequestSizeLimitMiddleware` や `ThrottleMiddleware` の近く
