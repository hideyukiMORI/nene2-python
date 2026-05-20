# Field Trial 45: SecurityHeadersMiddleware 詳細カスタマイズ実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.7 時点
**テーマ**: `SecurityHeadersMiddleware` の全オプション（CSP・HSTS・Permissions-Policy・extra_no_csp_paths）を組み合わせた実運用確認

---

## 概要

`SecurityHeadersMiddleware` の CSP カスタマイズ・HSTS 設定・Permissions-Policy カスタマイズ・
カスタム docs_url との組み合わせを実装した。
2 つの摩擦点を発見し、うち 1 件 (FP45-3) を修正した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft45-security-headers/` に以下を作成:

- **`app.py`** — カスタム `docs_url`/`openapi_url` + `SecurityHeadersMiddleware` 全オプション
- **`test_app.py`** — 静的ヘッダー・CSP・HSTS・Permissions-Policy・extra_no_csp_paths (12 件)
- **`test_friction.py`** — 摩擦点の確認テスト (4 件)

**テスト結果**: 16 件全通過 ✅

---

## 摩擦点

### FP45-1: カスタム docs_url 使用時に extra_no_csp_paths の設定を忘れやすい

**分類**: 軽微な摩擦（ドキュメント追記で対応）

FastAPI の `docs_url="/api/docs"` のようにカスタム URL を使う場合、
`SecurityHeadersMiddleware` のデフォルト `no_csp_paths` には
`/docs`・`/redoc`・`/openapi.json` しか含まれない。
`/api/docs` には CSP が付いてしまい、Swagger UI の CDN アセットが CSP でブロックされる。

```python
# カスタム docs_url 使用時の必須設定
app.add_middleware(
    SecurityHeadersMiddleware,
    extra_no_csp_paths=["/api/docs", "/api/redoc", "/api/openapi.json"],
)
```

**判断**: FT15 で実装した `extra_no_csp_paths` で対応可能だが、
デフォルトの `docs_url` を変更したときに `extra_no_csp_paths` も更新する必要があることを
ドキュメントで注意喚起する価値がある。

---

### FP45-2: HSTS は本番環境以外で有効にしてはならない

**分類**: 注意喚起（設計通り・ドキュメント記載済み）

`hsts` パラメータを設定すると、`Strict-Transport-Security` ヘッダーが付与される。
http:// でアクセスすると次回以降 https:// を強制するため、開発環境での誤設定に注意が必要。
`hsts=None` のデフォルトは意図的な安全設計。

**判断**: 設計通り。ドキュメントの Warning で注意喚起済み。

---

### FP45-3: csp="" のとき空の CSP ヘッダーが付与されていた

**分類**: バグ（#271 で修正）

`csp=""` を渡すと `Content-Security-Policy: ` という空ヘッダーが付与されていた。
ユーザーが CSP を無効化しようとして `csp=""` を渡すと、空 CSP が付く予期しない動作になる。

**修正**: `dispatch()` を `self._csp` が truthy のときのみ CSP ヘッダーを付与するよう変更。
`csp=""` は「CSP ヘッダーを付けない」として扱われる。

```python
# 修正前
if request.url.path not in self._no_csp_paths:
    response.headers["Content-Security-Policy"] = self._csp

# 修正後
if request.url.path not in self._no_csp_paths and self._csp:
    response.headers["Content-Security-Policy"] = self._csp
```

---

### FP45-4: 全オプション組み合わせは問題なく動作する

**分類**: 摩擦なし（設計の確認）

`csp`・`permissions_policy`・`hsts`・`extra_no_csp_paths` の全オプションを同時に指定しても
正常に動作することを確認した。

---

## フレームワーク変更

- `SecurityHeadersMiddleware.dispatch()` — `csp=""` のとき CSP ヘッダーを付与しないよう修正 (#271)

---

## 関連

- `nene2.middleware.SecurityHeadersMiddleware`
- FT15 (CSP カスタマイズ, v1.7.0)
- FT32 (HSTS・Permissions-Policy 追加, v1.8.3)
- Issue #271 (csp="" バグ修正)
