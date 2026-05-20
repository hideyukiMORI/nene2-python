# FT26: nene2.log structlog 統合検証

**日付**: 2026-05-20
**テーマ**: `setup_logging()` と `AppSettings.log_level` の連携検証
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft26-logging/`

---

## 目的

`nene2.log.setup_logging()` を実際のアプリで使い、
`AppSettings.log_level`（FT24 で追加）との統合フローを検証する。

---

## 実施内容

- `setup_logging()` の `local` / `production` 環境での動作確認
- `RequestLoggingMiddleware` と structlog の連携確認
- `AppSettings.log_level` を `setup_logging()` に渡す方法の検証

---

## テスト結果

### test_app.py（正常系・機能確認）
| テスト | 結果 |
|---|---|
| test_log_test_endpoint_returns_200 | PASS |
| test_request_logging_middleware_logs_request | PASS |
| test_log_levels_endpoint_returns_200 | PASS |
| test_setup_logging_local_env | PASS |
| test_setup_logging_production_env | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_setup_logging_does_not_accept_log_level_param | PASS | あり |
| test_setup_logging_hardcodes_info_level | PASS | あり |
| test_no_way_to_integrate_app_settings_log_level_with_setup_logging | PASS | あり（ボイラープレート） |

---

## 発見した摩擦点

### FT26-F1: setup_logging() が log_level を受け取れない

**概要**: FT24 で `AppSettings.log_level` が追加されたが、
`setup_logging()` はそれを受け取るパラメータを持たない。
`setup_logging()` は常に `logging.INFO` をハードコードするため、
`AppSettings.log_level = "DEBUG"` を設定しても反映されない。

```python
# 現状: ボイラープレートが必要
settings = AppSettings(log_level="DEBUG")
setup_logging(app_env=settings.app_env)
logging.getLogger().setLevel(settings.log_level)  # ← 別途必要

# 期待する使い方
setup_logging(app_env=settings.app_env, log_level=settings.log_level)
```

**期待する解決策**: `setup_logging(app_env="local", log_level="INFO")` のように
`log_level` パラメータを追加して `AppSettings` と統合しやすくする。

---

## まとめ

`setup_logging()` の基本機能（ConsoleRenderer / JSONRenderer の切り替え）は問題なく動作する。

摩擦点:
1. **`setup_logging()` に `log_level` パラメータがない** → `AppSettings.log_level` との統合時にボイラープレートが必要 → Issue 化・修正対象
