# Field Trial 52: ミドルウェアスタック組み合わせ検証

**Date**: 2026-05-20
**Theme**: 全ミドルウェアスタック (BearerToken + Throttle + RequestLogging + SecurityHeaders) の組み合わせ実運用
**Version under test**: v1.8.11
**FT App**: `/home/xi/docker/nene2-python-FT/ft52-middleware-stack/`

---

## 概要

`ErrorHandlerMiddleware` + `SecurityHeadersMiddleware` + `RequestIdMiddleware` +
`RequestLoggingMiddleware` + `ThrottleMiddleware` + `BearerTokenMiddleware` を
全スタックで積み重ねて動作を検証した。

---

## 実装内容

### ミドルウェアスタック

```python
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(SecurityHeadersMiddleware, csp="default-src 'self'", hsts="max-age=31536000")
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RequestLoggingMiddleware, exclude_paths=["/health"], extra_context={"service": "ft52", "env": "test"})
app.add_middleware(ThrottleMiddleware, limit=5, window=60, exclude_paths=["/health"])
app.add_middleware(BearerTokenMiddleware, verifier=verifier, exclude_paths=["/health", "/docs", "/openapi.json"])
```

`/health` は認証・ログ・レート制限をすべてバイパスする設計。

---

## テスト結果

10 tests, all passed (after fixing FP52-1).

| テスト | 結果 |
|---|---|
| /health は認証不要 | ✅ |
| /items は認証必須 | ✅ |
| 有効トークンで /items アクセス | ✅ |
| セキュリティヘッダー存在確認 | ✅ |
| HSTS ヘッダー確認 | ✅ |
| X-Request-Id ヘッダー確認 | ✅ |
| X-RateLimit-Limit ヘッダー確認 | ✅ |
| /health はレート制限なし (10回連続) | ✅ |
| レート制限超過で 429 | ✅ |
| 無効トークンで 401 | ✅ |

---

## 摩擦ポイント

### FP52-1: `LocalTokenVerifier` の引数名が直感的でない / `set` 非対応

**状況**: `LocalTokenVerifier(valid_tokens={valid_token})` と書いたが:
1. 引数名は `valid_tokens` ではなく `allowed_tokens`
2. `set` を渡すと型エラー（内部が `list[str]` を期待）

**修正**: `allowed_tokens` の型を `list[str] | set[str] | frozenset[str]` に変更し、
内部で `frozenset` に変換するよう修正 (#284)。
内部を `frozenset` にすることで `in` 演算の O(n) → O(1) 改善も得られた。

---

## フレームワーク変更

### `LocalTokenVerifier` — `set` / `frozenset` を受け入れ可能に (#284)

```python
# 修正前
def __init__(self, allowed_tokens: list[str]) -> None:
    self._allowed = allowed_tokens

# 修正後
def __init__(self, allowed_tokens: list[str] | set[str] | frozenset[str]) -> None:
    self._allowed: frozenset[str] = frozenset(allowed_tokens)
```

---

## 全スタック動作確認

各ミドルウェアの機能がスタック状態でも正常に動作することを確認:
- `exclude_paths` の設定が各ミドルウェアで独立して機能する
- `BearerTokenMiddleware` が `ThrottleMiddleware` より外側（先に評価）
- `SecurityHeadersMiddleware` のヘッダーが全レスポンスに付与される
- `RequestIdMiddleware` の `X-Request-Id` が全レスポンスに付与される
