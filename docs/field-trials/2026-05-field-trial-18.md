# Field Trial 18 — RequestLoggingMiddleware 実運用

**Date:** 2026-05-20
**App:** FT18 Request Logging API（structlog ログ・request_id 連携・JSON ログ形式検証）
**Directory:** `/home/xi/docker/nene2-python-FT/ft18-request-logging/`
**nene2-python version:** v1.7.0

## 概要

`RequestLoggingMiddleware` を `RequestIdMiddleware` と組み合わせて実際に動かし、
ログ出力の内容・request_id との連携・テストでのログ検証方法を確認した。

## 動作確認結果

- `request.received` / `request.completed` のログが出力されること ✓
- ログに `method`, `path`, `status_code`, `duration_ms` が含まれること ✓
- `RequestIdMiddleware` と組み合わせると `request_id` がログに入ること ✓
- ログに `request_id` が含まれ、レスポンスヘッダーの `X-Request-Id` と一致すること ✓

## 摩擦点

### FT18-F1 (MEDIUM, テスト容易性): structlog が pytest caplog で捕捉できない

`RequestLoggingMiddleware` は structlog を使ってログを出力するが、
structlog のデフォルト設定では Python stdlib の logging ハンドラーを経由せず
直接 stdout に書き込む。

そのため pytest の `caplog` では構造化ログを捕捉できない。
テストで `structlog` のログを検証するには `capsys` で stdout を捕捉するか、
structlog を stdlib logging に向ける設定変更が必要。

```python
# caplog では捕捉できない（摩擦）
with caplog.at_level(logging.INFO, logger="nene2.middleware.request_logging"):
    client.get("/health")
assert len(caplog.records) == 0  # 常に 0 — ログが入らない
```

**対応案**: `nene2.log` に `configure_for_testing()` ヘルパーを追加し、
テスト環境で `structlog` を stdlib logging ブリッジ経由で使える設定を提供する。

### FT18-F2 (LOW, 拡張性): ログレベルをコンストラクタから変更できない

`RequestLoggingMiddleware` は常に `logger.info()` を使う。
ヘルスチェックなど高頻度のパスのログを `DEBUG` に落としたい場合や、
特定パスのログを無効化したい場合にコンストラクタパラメータで設定できない。

他のミドルウェア（`ThrottleMiddleware` の `exclude_paths` など）との一貫性が取れていない。

**対応案**: `exclude_paths: list[str] | None = None` パラメータを追加して
特定パスのログを無効化できるようにする。または `log_level` パラメータで
デフォルトのログレベルを変更可能にする。

## まとめ

基本的なリクエストロギングは問題なく動作した。`RequestIdMiddleware` との連携も良好。
摩擦はテスト時の `caplog` 非対応（F1: MEDIUM）と拡張性（F2: LOW）の2点。

F1 は structlog の設計に起因するが、テスト用ヘルパーを提供することで改善できる。
F2 は他のミドルウェアとの一貫性の問題。
