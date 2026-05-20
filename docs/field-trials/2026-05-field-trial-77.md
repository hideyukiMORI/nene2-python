# FT77: BearerToken + ApiKey 混在認証

**日付**: 2026-05-20  
**テーマ**: 同一アプリで認証方式を混在させる — `/admin/*` は JWT Bearer、`/webhook/*` は API Key  
**バージョン**: v1.8.22  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft77-mixed-auth/`

---

## 概要

実運用では「認証方式がルートによって異なる」は非常に一般的なニーズ。
nene2 の `BearerTokenMiddleware` と `ApiKeyAuthMiddleware` を混在させる方法を検証した。
ミドルウェアはアプリ全体をカバーするため、`exclude_paths` を使った回避策が必要で、
ここに大きな摩擦があることが判明した。

---

## 実装したパターン

```
/admin/*   → BearerTokenMiddleware（JWT Bearer 必須）
/webhook/* → ApiKeyAuthMiddleware（X-Api-Key 必須）
/public/*  → 認証不要
```

### 設定コード

```python
app.add_middleware(
    BearerTokenMiddleware,
    verifier=admin_verifier,
    exclude_paths=[
        "/docs", "/openapi.json", "/redoc", "/health",
        "/public/hello", "/public/status",
        "/webhook/event", "/webhook/ping",  # ← webhook は除外
    ],
)

app.add_middleware(
    ApiKeyAuthMiddleware,
    verifier=webhook_verifier,
    exclude_paths=[
        "/docs", "/openapi.json", "/redoc", "/health",
        "/public/hello", "/public/status",
        "/admin/dashboard", "/admin/users",  # ← admin は除外
    ],
)
```

---

## 発見した問題

### 問題1: exclude_paths の二重管理

認証対象でないパスを **各ミドルウェアに個別に列挙** しなければならない。

- 新しい `/admin/settings` ルートを追加 → `ApiKeyAuthMiddleware` の `exclude_paths` にも追加必要
- 忘れると: Bearer トークンを持っていても、API Key がないため 401 になる
- **サイレント障害**: 認証エラーなので「なぜ 401？」と混乱しやすい

### 問題2: exclude_paths はルートではなく完全一致パス

`exclude_paths` はプレフィックスマッチングをサポートしない。

```python
# ❌ プレフィックスマッチしない
exclude_paths=["/admin"]  # /admin/dashboard にマッチしない

# ✅ 完全一致のみ
exclude_paths=["/admin/dashboard", "/admin/users"]  # 各パスを列挙
```

ルート数が増えると管理が煩雑になる。

### 問題3: per-route 認証デコレーターがない

FastAPI の Depends() パターンでルートごとに認証を指定することが nene2 では直接できない。

```python
# FastAPI 標準 (nene2 提供なし)
from fastapi.security import HTTPBearer
security = HTTPBearer()

@app.get("/admin/dashboard")
def admin(token = Depends(security)):
    ...
```

nene2 でこれをやるには生の FastAPI `Depends()` を使う必要があり、
nene2 の `TokenVerifierProtocol` との統合方法が不明瞭。

### 問題4: 「どちらかで認証」が実現できない

Bearer でも API Key でも OK という「OR 認証」がミドルウェア方式では実現困難。

```
# 現状では:
BearerMiddleware: 対象パスはBearer必須
ApiKeyMiddleware: 対象パスはApiKey必須

# 実現できない:
"Bearer OR ApiKey どちらかがあれば OK"
```

---

## テスト結果（全17件パス）

```
test_public_hello_no_auth               PASSED  # 公開エンドポイント
test_public_status_no_auth              PASSED
test_health_no_auth                     PASSED
test_admin_with_valid_bearer            PASSED  # 正常認証
test_admin_without_auth_returns_401     PASSED
test_admin_with_invalid_bearer_returns_401  PASSED
test_admin_with_api_key_instead_of_bearer_returns_401  PASSED  # 認証方式が違う
test_admin_users_with_valid_bearer      PASSED
test_webhook_with_valid_api_key         PASSED
test_webhook_without_auth_returns_401   PASSED
test_webhook_with_invalid_api_key_returns_401  PASSED
test_webhook_with_bearer_instead_of_api_key_returns_401  PASSED
test_admin_with_both_headers_bearer_wins  PASSED  # 両方送ると適切に処理
test_webhook_with_both_headers_apikey_wins  PASSED
test_friction_new_admin_route_needs_exclude_update  PASSED  # 摩擦の記録
test_friction_exclude_paths_is_per_middleware  PASSED
test_nene2_has_no_per_route_auth_decorator  PASSED  # per-route 機能なし確認
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F77-1 | exclude_paths の二重管理 — 新ルートを追加するたびに各ミドルウェアを更新 | 高 |
| F77-2 | exclude_paths がプレフィックスマッチをサポートしない（完全一致のみ）| 中 |
| F77-3 | per-route 認証デコレーターがない — Depends() との統合方法が不明 | 中 |
| F77-4 | Bearer OR ApiKey の OR 認証が実現できない | 中 |

---

## 使用感（主観評価）

### 直感性 ★★☆☆☆

「ミドルウェアは全体をカバーする」という原則は理解できる。
しかし「特定のルートだけ認証したい」という非常に一般的なニーズに、
`exclude_paths` という「否定のリスト」で対応するのは直感に反する。

Express の `passport.authenticate()` や Spring Security の `requestMatchers()` は
「守りたいパスを指定」するモデル。nene2 は「除外するパスを指定」という逆のモデルで混乱しやすい。

### 実害の深刻さ ★★★★☆

新しいルートを追加したとき、`exclude_paths` の更新を忘れると **サイレントな認証エラー** が発生する。
本番でユーザーが急に 401 になり、コードを読んでも一見問題がないように見える。
ミドルウェアの設定を疑わないと根本原因に辿り着けない。

### 修正のしやすさ ★★★☆☆

根本解決は「プレフィックスマッチ対応」または「per-route auth」の提供。
プレフィックスマッチは小さな変更で実現できる。
per-route auth の提供は FastAPI Depends() との統合が必要で中程度の工数。

### 総合コメント

「守りたいパスのプレフィックスを指定する」モデルへの転換が最も効果的。
`include_paths: list[str] | None` または `path_prefix: str` パラメーターを追加するだけで、
「`/admin` 以下は全部 Bearer 必須」と書けるようになり、UX が大幅に改善する。

---

## 推奨アクション

1. **Issue**: `BearerTokenMiddleware` / `ApiKeyAuthMiddleware` に `include_paths` または `path_prefixes` パラメーターを追加
2. **Issue**: `exclude_paths` にプレフィックスマッチ（`/admin/*` 形式）をサポート
3. **将来**: `nene2.auth` に FastAPI `Depends()` 統合ヘルパーを提供
