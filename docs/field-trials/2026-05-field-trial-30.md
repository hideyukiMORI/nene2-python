# FT30: RequestLoggingMiddleware + structlog バインディング実運用検証

**日付**: 2026-05-20
**テーマ**: `RequestLoggingMiddleware` と structlog contextvars の実運用パターン検証
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft30-request-logging/`

---

## 目的

`RequestLoggingMiddleware` と structlog の contextvars 統合を実際のアプリで検証し、
カスタムフィールドの付加方法を確認する。

---

## 実施内容

- `RequestLoggingMiddleware` が自動バインドするコンテキスト（request_id, method, path）を確認
- 追加のコンテキストフィールドを渡す方法を検証
- `clear_contextvars()` の挙動確認

---

## テスト結果

### test_app.py（正常系・機能確認）
| テスト | 結果 |
|---|---|
| test_log_test_endpoint_returns_200 | PASS |
| test_with_user_context_returns_200 | PASS |
| test_request_id_is_in_response_header | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_clear_contextvars_wipes_pre_bound_context | PASS | 軽微（設計上の制限） |
| test_no_way_to_add_extra_fields_to_request_log | PASS | あり |

---

## 発見した摩擦点

### FT30-F1: RequestLoggingMiddleware に extra_context パラメータがない

**概要**: `service_name` や `version` などの静的フィールドを全リクエストログに含めたい場合、
`RequestLoggingMiddleware` にパラメータとして渡す方法がない。

```python
# 期待する使い方
app.add_middleware(
    RequestLoggingMiddleware,
    extra_context={"service": "my-api", "version": "1.0.0"},
)
```

**期待する解決策**: `extra_context: dict[str, str] | None = None` パラメータを追加し、
`bind_contextvars()` に追加フィールドとして渡す。

---

## まとめ

`RequestLoggingMiddleware` の基本機能は問題なく動作する。

摩擦点:
1. **`extra_context` パラメータがない** → Issue 化・修正対象
