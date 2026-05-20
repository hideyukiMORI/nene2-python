# Field Trial 99: Webhook HMAC-SHA256 署名検証

## テーマ

外部サービス（GitHub / Stripe 方式）からの Webhook を HMAC-SHA256 署名で検証するパターンを nene2 上で実装する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft99-webhook-hmac/` に以下を実装:

- GitHub 方式: `X-Hub-Signature-256: sha256=<hex>` ヘッダーを HMAC-SHA256 で検証
- Stripe 方式: `Stripe-Signature: t=<timestamp>,v1=<hex>` 形式の署名を検証
- `hmac.compare_digest()` による timing-safe 比較
- `await request.body()` + `await request.json()` の二重読み取りパターン

## テスト結果

全 7 テスト通過。

## Friction Points

### FP1: nene2 に Webhook 署名検証ユーティリティがない

**状況**: GitHub/Stripe 方式の HMAC 署名検証は頻出パターンだが、nene2 に `verify_webhook_signature()` のようなユーティリティが存在しない。毎回 `hmac` モジュールを直接扱う必要がある。

**影響**: `hmac.new()` / `hmac.compare_digest()` を知らない開発者が `==` 比較を使い、timing attack に脆弱な実装をしてしまうリスクがある。

**期待する API**:
```python
from nene2.security import verify_hmac_signature

# GitHub 方式
verify_hmac_signature(body, secret, header_value, prefix="sha256=")

# Stripe 方式
verify_stripe_signature(body, secret, header_value)
```

### FP2: `await request.body()` → `await request.json()` の二重読み取りがドキュメント化されていない

**状況**: Webhook 署名検証では生バイト（`request.body()`）を HMAC に通してから、JSONとしてパース（`request.json()`）する二重読み取りが必要。FastAPI は内部でボディをキャッシュするため動作するが、この挙動はフレームワークに依存した暗黙の知識。

**影響**: 「一度 `body()` を読んだら `json()` は使えない」と誤解して `json.loads(body)` を書く開発者が出る。

**期待するドキュメント**: how-to に「Webhook ハンドラーでの生ボディ + JSON 二重読み取りパターン」を追加。

### FP3: BearerTokenMiddleware は Webhook 認証に使えない

**状況**: nene2 の `BearerTokenMiddleware` は Bearer トークン認証に特化しており、HMAC 署名検証（リクエストボディを使った認証）には対応しない。Webhook エンドポイントでは `exclude_paths` で除外して自前検証するか、専用の Depends 関数を書く必要がある。

**影響**: 摩擦は低いが、「nene2 の認証機構でWebhookも守れる」という誤解が生まれやすい。

**期待するドキュメント**: how-to に「Webhook 署名検証 vs Bearer Token 認証の使い分け」を明記。

## まとめ

Webhook HMAC 検証自体は Python 標準ライブラリで実装できるが、セキュアな実装（timing-safe 比較）のためのユーティリティがないため FP1 として Issue を起票する。FP2・FP3 はドキュメント摩擦。
