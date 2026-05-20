# FT59: SecurityHeadersMiddleware 実運用検証

**日付**: 2026-05-20  
**テーマ**: セキュリティヘッダーミドルウェア (`SecurityHeadersMiddleware`) の実運用確認  
**バージョン**: v1.8.15  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft59-security-headers/`

---

## 概要

`nene2.middleware.SecurityHeadersMiddleware` を FastAPI に組み込み、
デフォルトヘッダー・CSP・HSTS・除外パス設定を検証した。

---

## 実装内容

- デフォルト設定でのセキュリティヘッダー確認
- カスタム CSP / Permissions-Policy の適用
- HSTS ヘッダーの条件付き付与（デフォルト無効、本番向け）
- `/docs`, `/redoc`, `/openapi.json` での CSP 自動スキップ
- `extra_no_csp_paths` によるカスタムパスの CSP 除外

---

## テスト結果

**10/10 passed**

| テスト | 結果 |
|---|---|
| `test_default_static_headers_present` | PASSED |
| `test_default_csp_applied` | PASSED |
| `test_default_permissions_policy_applied` | PASSED |
| `test_hsts_not_set_by_default` | PASSED |
| `test_hsts_applied_when_configured` | PASSED |
| `test_csp_skipped_for_docs_paths` | PASSED |
| `test_custom_csp_applied` | PASSED |
| `test_custom_permissions_policy_applied` | PASSED |
| `test_extra_no_csp_paths_skip_csp` | PASSED |
| `test_extra_no_csp_paths_does_not_affect_other_paths` | PASSED |

---

## Friction Points

なし。`SecurityHeadersMiddleware` はすべての機能が直感的に動作した。

**特筆点**:
- OpenAPI パス (`/docs`, `/redoc`, `/openapi.json`) での CSP 自動スキップは、
  Swagger UI の CDN アセット読み込みが壊れないよう配慮されており実用的
- HSTS がデフォルト無効なのは開発環境を壊さないための正しい設計
- `extra_no_csp_paths` でカスタムドキュメントパスも対応できる柔軟性がある

---

## 結論

`SecurityHeadersMiddleware` は実運用で問題なく使用できる。
デフォルト設定のみで OWASP 推奨の主要ヘッダーが付与され、
本番環境では `hsts` パラメータを追加するだけでよい。
