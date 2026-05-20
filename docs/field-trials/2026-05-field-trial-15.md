# Field Trial 15 — SecurityHeadersMiddleware 実運用

**Date:** 2026-05-20
**App:** FT15 Security Headers API（セキュリティヘッダーの付与・CSP 動作確認）
**Directory:** `/home/xi/docker/nene2-python-FT/ft15-security-headers/`
**nene2-python version:** v1.6.0

## 概要

`SecurityHeadersMiddleware` を実際のアプリに組み込み、各ヘッダーの付与動作・
CSP スキップロジック・カスタマイズ可能性を検証した。

## 動作確認結果

- 通常エンドポイントに `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`, `Permissions-Policy` の全ヘッダーが付与されること ✓
- `/docs`, `/redoc`, `/openapi.json` では `Content-Security-Policy` がスキップされること ✓
- CSP スキップ時も他のヘッダーは引き続き付与されること ✓

## 摩擦点

### FT15-F1 (MEDIUM, 拡張性): カスタム OpenAPI パスで CSP スキップが効かない

`SecurityHeadersMiddleware` がスキップする OpenAPI パスは `_OPENAPI_PATHS` 定数で
`{"/docs", "/redoc", "/openapi.json"}` にハードコードされている。

FastAPI では `docs_url` / `redoc_url` でカスタムパスを設定できるが、
カスタムパス（例: `/api-docs`）では CSP スキップが効かず、Swagger UI が CDN アセットを
ブロックされる可能性がある。

```python
app = FastAPI(docs_url="/api-docs", redoc_url="/api-redoc")
app.add_middleware(SecurityHeadersMiddleware)
# → /api-docs に CSP "default-src 'self'" が付いてしまう
```

**対応**: コンストラクタに `extra_no_csp_paths: list[str] | None = None` を追加し、
ユーザーがカスタム OpenAPI パスを指定できるようにする。または `ThrottleMiddleware` と
同様の `exclude_paths` パターンで完全スキップを可能にする。

### FT15-F2 (LOW, 拡張性): CSP をコンストラクタで上書きできない

CSP の値 `"default-src 'self'"` はモジュールレベルの `_HEADERS` 定数にハードコードされており、
コンストラクタから上書きできない。

CDN アセットを許可したい（`content-src 'self' cdn.example.com`）など、
CSP を変更したいユーザーは `_HEADERS` をモジュールレベルで直接書き換えるしかなく、
グローバルな副作用が発生する。

```python
# 現状の唯一の方法（副作用あり）
from nene2.middleware import security_headers
security_headers._HEADERS["Content-Security-Policy"] = "default-src 'self' cdn.example.com"
```

**対応**: `SecurityHeadersMiddleware(csp: str | None = None)` でコンストラクタから
CSP 値を上書きできるようにする。

## まとめ

基本動作は問題なし。全セキュリティヘッダーの付与・OpenAPI パスでの CSP スキップも
正常に機能した。摩擦は拡張性の面で2点あり：

- FT15-F1 (MEDIUM): カスタム OpenAPI パスで CSP スキップが効かない
- FT15-F2 (LOW): CSP 値をコンストラクタから変更できない

`ThrottleMiddleware` が `exclude_paths` を持つのに対し、`SecurityHeadersMiddleware` は
カスタマイズポイントがゼロであるため、実用アプリでの柔軟性が低い。
