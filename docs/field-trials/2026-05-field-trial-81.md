# FT81: CORS 設定 — setup_middlewares() と CORSMiddleware の組み合わせ

**日付**: 2026-05-20  
**テーマ**: setup_middlewares() に CORS サポートがない場合の正しい設定パターン検証  
**バージョン**: v1.8.26  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft81-cors/`

---

## 概要

nene2 の `setup_middlewares()` は CORS をサポートしていないため、
ブラウザから API を呼び出すアプリで CORS が必要になった際に
ユーザーは `CORSMiddleware` を手動で追加する必要がある。
その際、Starlette の LIFO ミドルウェア順序を理解していないと
OPTIONS プリフライトが正常に動作しない問題を確認した。

---

## 実装パターン

### 正しい CORS 設定（CORS を最外側に配置）

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from nene2.middleware import setup_middlewares

ALLOWED_ORIGINS = [
    "https://app.example.com",
    "https://admin.example.com",
]

app = FastAPI()

# ✅ CORS を先に add_middleware → setup_middlewares() 後は LIFO で最外側になる
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
)
setup_middlewares(app)
```

### 間違ったパターン（CORS が内側になる）

```python
# ❌ setup_middlewares() の後に CORS を追加すると内側に入る
app = FastAPI()
setup_middlewares(app)
app.add_middleware(CORSMiddleware, allow_origins=["https://app.example.com"])
# → OPTIONS プリフライトが nene2 ミドルウェアに遮断される可能性がある
```

### 禁止パターン（CLAUDE.md ポリシー違反）

```python
# ❌ CLAUDE.md 明示禁止: allow_origins=["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # セキュリティリスク
)
```

---

## 発見した問題

### 問題1: setup_middlewares() に CORS パラメーターがない

```python
# CORS が必要でも setup_middlewares() のシグネチャに cors パラメーターなし
setup_middlewares(
    app,
    # cors_allowed_origins=["https://app.example.com"],  # 存在しない
)
```

ユーザーは `FastAPI.add_middleware(CORSMiddleware, ...)` を直接呼ぶ必要がある。
FastAPI/Starlette のドキュメントを参照しなければ方法がわからない。

### 問題2: ミドルウェア順序が直感に反する（LIFO）

```python
# Starlette は LIFO — 最後に add_middleware したものが最外側になる
# つまり CORS を「最外側にしたい」なら「最初に add する」

app.add_middleware(CORSMiddleware, ...)  # ← 先に追加 = 最外側（正しい）
setup_middlewares(app)                   # ← 後から追加 = 内側

# 逆にすると:
setup_middlewares(app)                   # ← 先に追加 = 最内側（危険）
app.add_middleware(CORSMiddleware, ...)  # ← 後から追加 = 最外側になってしまう
```

「最外側に置きたいなら先に add する」という反直感的な順序。

### 問題3: nene2 が allow_origins=["*"] を禁止しない

```python
# CLAUDE.md で明示禁止されているが、nene2 フレームワークは検証しない
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 禁止ポリシーだが動作してしまう
)
```

フレームワークレベルで `ValueError` を raise することも可能だが、
`setup_middlewares()` を経由しない場合は検証できない。

### 問題4: 複数オリジン・credentials 設定パターンがドキュメントにない

本番アプリでは複数オリジン（本番環境 + ステージング環境）や
`allow_credentials=True` が必要なケースが多いが、
nene2 のドキュメントにこのパターンの記載がない。

---

## テスト結果（全13件パス）

```
test_list_items_returns_200                            PASSED
test_create_item_returns_201                           PASSED
test_cors_allowed_origin_returns_access_control_header PASSED
test_cors_disallowed_origin_no_access_control_header   PASSED
test_cors_preflight_options_returns_200                PASSED  # OPTIONS プリフライト正常動作
test_cors_preflight_disallowed_origin                  PASSED
test_cors_credentials_allowed                          PASSED
test_security_headers_present_with_cors               PASSED  # nene2 ミドルウェアと共存
test_request_id_present_with_cors                     PASSED  # X-Request-Id と共存
test_friction_no_cors_in_setup_middlewares             PASSED  # 摩擦: CORS パラメーターなし
test_friction_cors_order_matters                       PASSED  # 摩擦: LIFO 順序問題
test_friction_wildcard_origin_is_insecure              PASSED  # 摩擦: ["*"] を止めない
test_friction_multiple_origins_not_documented          PASSED  # 摩擦: ドキュメント不足
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F81-1 | `setup_middlewares()` に CORS パラメーターがなく手動追加が必要 | 中 |
| F81-2 | Starlette の LIFO 順序を知らないと OPTIONS プリフライトが壊れる | 中 |
| F81-3 | `allow_origins=["*"]` を nene2 が禁止しない（ポリシーのみ） | 低 |
| F81-4 | 複数オリジン・credentials パターンがドキュメントに未記載 | 低 |

---

## 使用感（主観評価）

### 直感性 ★★★☆☆

`setup_middlewares()` を使うと CORS は自分で追加しなければならず、
しかも「先に add する = 最外側になる」という反直感的な順序ルールがある。
FastAPI や Express.js、Spring Security の CORS 設定を知っているユーザーでも
nene2 特有の LIFO 順序で一度はつまずく。

### 実害の深刻さ ★★★☆☆

ブラウザからの CORS エラーは「API が動かない」として即座に表面化する。
原因が「ミドルウェア順序」であることを特定するのに時間がかかることがある。
特に OPTIONS プリフライトが通らないと PUT/DELETE/POST with Auth が全滅する。

### 修正のしやすさ ★★★★★

`setup_middlewares()` に `cors_allowed_origins` パラメーターを追加するだけ。
CORS は最外側（最初の add_middleware）に固定できるため、
ユーザーが順序を気にする必要がなくなる。

```python
# 理想の API:
setup_middlewares(
    app,
    cors_allowed_origins=["https://app.example.com"],
    cors_allow_credentials=True,
)
```

### 総合コメント

CORS は「作ったら必ず必要になる」機能でありながら、
nene2 の `setup_middlewares()` には組み込まれていない。
`["*"]` 禁止は CLAUDE.md のポリシーとして正しいが、
フレームワークが強制しないと誰かが違反する。
`cors_allowed_origins` を追加してワイルドカードを `ValueError` にすれば
セキュリティポリシーをコードで強制できる。

---

## 推奨アクション

1. **Issue**: `setup_middlewares()` に `cors_allowed_origins` パラメーターを追加
   — `allow_origins=["*"]` を渡した場合に `ValueError` を raise
   — CORS を最外側に自動配置（ユーザーが順序を意識しなくていい）
2. **docs**: 複数オリジン・credentials のパターンを how-to ガイドに追加
