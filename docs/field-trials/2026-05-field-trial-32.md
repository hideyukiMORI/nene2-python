# FT32: SecurityHeadersMiddleware CSP カスタマイズ実運用検証

**日付**: 2026-05-20
**テーマ**: `SecurityHeadersMiddleware` のカスタマイズ可能性検証
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft32-security-headers/`

---

## 目的

`SecurityHeadersMiddleware` の CSP カスタマイズ機能を実際のアプリで検証し、
ハードコードされたヘッダーの問題を記録する。

---

## 実施内容

- デフォルトセキュリティヘッダーの確認
- カスタム CSP の適用確認
- `extra_no_csp_paths` の動作確認
- ハードコードされたヘッダーの制限を確認

---

## テスト結果

### test_app.py（正常系・機能確認）
| テスト | 結果 |
|---|---|
| test_default_security_headers_present | PASS |
| test_default_csp_is_default_src_self | PASS |
| test_custom_csp_is_applied | PASS |
| test_docs_path_has_no_csp | PASS |
| test_extra_no_csp_paths_skip_csp | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_permissions_policy_is_hardcoded | PASS | あり |
| test_no_hsts_header | PASS | あり |
| test_x_frame_options_is_hardcoded_to_deny | PASS | あり（軽微） |

---

## 発見した摩擦点

### FT32-F1: Permissions-Policy がハードコードされている

**概要**: `geolocation=(), microphone=()` が固定値でカスタマイズできない。
位置情報 API を使うアプリでは `geolocation=(self)` に変更できない。

**期待する解決策**: `permissions_policy: str | None = None` パラメータを追加。

### FT32-F2: HSTS ヘッダーがない

**概要**: production 環境では `Strict-Transport-Security` を設定すべきだが、
`SecurityHeadersMiddleware` は HSTS を付与しない。
開発環境では不要なため、オプションとして設定できるべき。

**期待する解決策**: `hsts: str | None = None` パラメータを追加。

### FT32-F3: X-Frame-Options が DENY にハードコード（軽微）

**概要**: iframe 内表示が必要なケースで SAMEORIGIN に変更できない。
ただし DENY がセキュリティ上より安全なデフォルトであり、一般ユース向け。

**判断**: ニッチなケースのため低優先度。Issue 化はするが即座に修正しない。

---

## まとめ

CSP カスタマイズ機能は問題なく動作する。

摩擦点:
1. **Permissions-Policy ハードコード** → Issue 化・修正対象
2. **HSTS ヘッダーなし** → Issue 化・修正対象
3. **X-Frame-Options ハードコード** → 低優先度 Issue
