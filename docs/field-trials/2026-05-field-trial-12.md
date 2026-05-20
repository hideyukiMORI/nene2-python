# Field Trial 12 — ThrottleMiddleware + RequestSizeLimitMiddleware 実運用

**Date:** 2026-05-20
**App:** Chirp API（短文投稿 API、レート制限 + ペイロード制限付き）
**Directory:** `/home/xi/docker/nene2-python-FT/ft12-throttle/`
**nene2-python version:** v1.4.0

## 概要

`ThrottleMiddleware`（固定ウィンドウレート制限）と `RequestSizeLimitMiddleware`（リクエストボディ制限）を実際のアプリに組み込み、動作と摩擦点を確認した。

## 動作確認結果

- `ThrottleMiddleware(limit=3, window=60)` で3リクエスト後に 429 + `Retry-After` ヘッダーが返ること ✓
- `RequestSizeLimitMiddleware(max_bytes=100)` でペイロード超過時に 413 が返ること ✓
- 両ミドルウェアとも Problem Details (RFC 9457) 形式でエラーレスポンスが返ること ✓
- `AppSettings` に `throttle_limit`, `throttle_window`, `max_body_size` が揃っていること ✓

## 摩擦点

### FT12-F1 (MEDIUM): ThrottleMiddleware に exclude_paths がない

BearerTokenMiddleware・ApiKeyAuthMiddleware は FT11 で `exclude_paths` を追加したが、
`ThrottleMiddleware` には同パラメータがない。

```python
# やりたいこと: /health はレート制限の対象外にしたい
app.add_middleware(
    ThrottleMiddleware,
    limit=60,
    window=60,
    exclude_paths=["/health", "/docs"],  # ← 存在しない
)
```

実際には `/health` も 60req/min のレート制限にかかる。ロードバランサーのヘルスチェックが
高頻度で叩く環境では 429 が返り、インスタンスがダウン扱いになるリスクがある。

**再現コード:**
```python
app.add_middleware(ThrottleMiddleware, limit=2, window=60)
# /health を3回叩くと3回目が 429
```

### FT12-F2 (MEDIUM): RequestSizeLimitMiddleware に exclude_paths がない

同様に `RequestSizeLimitMiddleware` にも `exclude_paths` がない。
実用上の影響は ThrottleMiddleware より小さいが（GET リクエストはボディなしなので通常問題ない）、
一貫性の観点から揃えるべき。

BearerTokenMiddleware, ApiKeyAuthMiddleware, ThrottleMiddleware がすべて `exclude_paths` を
持つのに RequestSizeLimitMiddleware だけ持たない状態は混乱を招く。

## まとめ

基本動作は問題なし。FT11 で auth 系ミドルウェアに `exclude_paths` を追加したが、
同じ修正が `ThrottleMiddleware` と `RequestSizeLimitMiddleware` にも必要。
3つのミドルウェアで `exclude_paths` の有無が揃っていないことが主な摩擦。
