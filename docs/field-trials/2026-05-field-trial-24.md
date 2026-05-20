# FT24: AppSettings 実運用検証

**日付**: 2026-05-20
**テーマ**: `AppSettings` を使った環境変数ベースの設定管理パターンの実運用検証
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft24-app-settings/`

---

## 目的

`nene2.config.AppSettings` を実際のアプリに組み込み、
環境変数から設定を読み込んでミドルウェアを設定するパターンを検証する。

---

## 実施内容

`AppSettings` の各フィールドを使って以下を設定:
- `ErrorHandlerMiddleware(debug=settings.app_debug)`
- `RequestSizeLimitMiddleware(max_bytes=settings.max_body_size)`
- `ThrottleMiddleware(limit=settings.throttle_limit, window=settings.throttle_window)` (conditional)
- `SecurityHeadersMiddleware` (conditional)

---

## テスト結果

### test_app.py（正常系・機能確認）
| テスト | 結果 |
|---|---|
| test_health_endpoint_returns_env | PASS |
| test_debug_false_by_default | PASS |
| test_settings_loaded_from_env_vars | PASS |
| test_throttle_disabled_via_settings | PASS |
| test_max_body_size_from_settings | PASS |
| test_db_url_sqlite_default | PASS |
| test_db_url_mysql_format | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_list_fields_not_parseable_from_env_string | PASS | あり（ドキュメント） |
| test_no_log_level_setting | PASS | あり |
| test_no_middleware_factory_helper | PASS | あり（設計上の判断） |

---

## 発見した摩擦点

### FT24-F1: list[str] フィールドを環境変数で設定する方法がドキュメントにない

**概要**: `cors_origins`、`bearer_tokens`、`api_keys` は `list[str]` 型だが、
環境変数から設定するには JSON 形式 (`["a","b"]`) が必要。
単純な `"token1,token2"` ではパースされない。

**判断**: pydantic-settings の標準動作のため、リファレンスドキュメントに記載する。

---

### FT24-F2: ログレベルの設定フィールドがない

**概要**: `app_debug: bool` しかなく、`INFO`/`WARNING`/`ERROR` の粒度制御ができない。

**影響**: ステージング環境で `INFO` ログを出しつつ、本番では `WARNING` に絞りたいが、
現在は `app_debug=true` でしか詳細ログを出す方法がない。

**期待する解決策**: `log_level: str = "INFO"` フィールドを追加。

---

### FT24-F3: AppSettings からミドルウェアを自動設定するヘルパーがない

**概要**: AppSettings の設定値をミドルウェアに適用するには、
毎回条件分岐付きのボイラープレートを手書きする必要がある。

**判断**: `configure_middleware(app, settings)` ヘルパーは「薄い HTTP 層」の設計哲学に反し、
フレームワークの主張が強くなりすぎる。FT アプリ側でパターンを提示する対応が適切。
今回はドキュメント追加のみ。

---

## まとめ

`AppSettings` は環境変数から型安全に設定を読み込む機能として正しく動作する。
実運用での摩擦は:

1. **list[str] 環境変数の書き方がわかりにくい** → ドキュメント追加対応
2. **log_level フィールドがない** → Issue 化・修正対象
3. **ミドルウェア自動設定ヘルパーがない** → 設計上の判断で修正しない
