# Field Trial 43: ThrottleMiddleware path_limits 実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.6 時点
**テーマ**: `ThrottleMiddleware` の `path_limits` パラメータを使ってエンドポイントごとにレート制限を設定するパターンの実運用確認

---

## 概要

グローバルレート制限（`limit=100`）と、特定パスへの厳しい制限（`path_limits={"/api/search": 10, "/api/upload": 5}`）を組み合わせた API を実装し、動作を確認した。
レートカウンターがパスごとに独立して管理されること、`X-RateLimit-*` ヘッダーが適切に付与されることを検証した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft43-throttle-path-limits/` に以下を作成:

- **`app.py`** — グローバル + パスごとのレート制限設定、`/health` 除外パスの構成
- **`test_app.py`** — 正常系・ヘッダー確認・path_limits 独立性・429 動作 (10 件)
- **`test_friction.py`** — 摩擦点の確認テスト (4 件)

**テスト結果**: 14 件全通過 ✅

---

## 摩擦点

### FP43-1: path_limits のカウンターはグローバルカウンターと完全に独立している

**分類**: 摩擦なし（良い設計の確認）

`path_limits` に指定したパスは `{client}:{path}` をキーとして使い、
グローバルカウンター (`{client}`) とは別々に管理される。
`/api/search` を使い切っても `/api/items` のカウンターには影響しない。

```python
# /api/search の制限 (3 req) を使い切っても
for _ in range(3):
    client.get("/api/search")
# /api/items の制限は消費されていない
r = client.get("/api/items")
assert r.status_code == 200  # OK
```

**判断**: FT28 で実装した設計通り。パス別独立カウンターは想定通りに動作する。

---

### FP43-2: X-RateLimit-Limit ヘッダーがパスごとの制限値を反映する

**分類**: 摩擦なし（良い設計の確認）

`/api/search` へのリクエストには `X-RateLimit-Limit: 3` が付与され、
`/api/items` へのリクエストには `X-RateLimit-Limit: 10` が付与される。
クライアントはヘッダーを見て自分のリミットがいくつかを判断できる。

**判断**: FT20 で実装したヘッダー付与が path_limits と正しく連携している。

---

### FP43-3: X-Forwarded-For がクライアントキーとして使われるためバイパスに注意

**分類**: 設計上の制約（ドキュメントに記載済み・運用上の注意点）

`X-Forwarded-For` ヘッダーがある場合、それをクライアント IP として使う設計のため、
異なる `X-Forwarded-For` を送ることで別のクライアントとして扱われ、レート制限をバイパスできる。

```python
# 通常の IP で制限を使い切ったあと
for _ in range(2):
    client.get("/api/items")
r = client.get("/api/items")
assert r.status_code == 429

# 別の IP を騙って送ると 200 になる
r = client.get("/api/items", headers={"X-Forwarded-For": "10.0.0.1"})
assert r.status_code == 200  # バイパスできてしまう
```

**判断**: ドキュメントの Warning セクションに記載されている既知の制限。
信頼できるリバースプロキシを前段に置くことで軽減できる。
テスト環境での動作確認として有用。

---

### FP43-4: path_limits の対象外パスはグローバル制限のみが適用される

**分類**: 摩擦なし（設計の確認）

`path_limits` に指定していないパス (`/api/items` など) はグローバルの `limit` が適用される。
複数のエンドポイントに異なる制限を設けつつ、デフォルトのグローバル制限を基本として使う設計が自然に実現できる。

**判断**: FT28 の設計通り。`path_limits` に指定のないパスは `{client}` をキーに使い、グローバルカウンターで管理される。

---

## フレームワーク変更

なし（全て設計通りの挙動）

---

## 関連

- `nene2.middleware.ThrottleMiddleware` (FT20, v1.8.0)
- `ThrottleMiddleware.path_limits` (FT28, v1.8.1)
- `ThrottleMiddleware` ウィンドウクリーンアップ (FT27, v1.8.1)
- FT20 (ThrottleMiddleware ヘッダー実装, v1.8.0)
- FT27 (ThrottleMiddleware クリーンアップ修正, v1.8.1)
- FT28 (ThrottleMiddleware path_limits 実装, v1.8.1)
