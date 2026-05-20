# FT79: RequestLoggingMiddleware と構造化ログ

**日付**: 2026-05-20  
**テーマ**: リクエストログに何が含まれるか — 機密情報漏洩リスクとデバッグ適性の確認  
**バージョン**: v1.8.24  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft79-request-logging/`

---

## 概要

`RequestLoggingMiddleware` と `structlog` の組み合わせを検証した。
基本機能は期待通り動作し、セキュリティ設計（ボディをログしない）も適切。
一方で、リクエストボディの選択的ログ記録やリクエストごとの動的コンテキスト追加といった
デバッグ用途での柔軟性の欠如が摩擦点として判明した。

---

## ログ出力の内容（確認済み）

### request.received

```json
{
  "event": "request.received",
  "level": "info",
  "logger": "nene2.middleware.request_logging",
  "method": "GET",
  "path": "/api/users",
  "request_id": "abc-123",
  "service": "ft79-app",
  "version": "1.0.0"
}
```

### request.completed

```json
{
  "event": "request.completed",
  "level": "info",
  "logger": "nene2.middleware.request_logging",
  "method": "GET",
  "path": "/api/users",
  "status_code": 200,
  "duration_ms": 1.4,
  "request_id": "abc-123",
  "service": "ft79-app",
  "version": "1.0.0"
}
```

---

## セキュリティ設計（良い点）

### リクエストボディをログしない ✅

```python
# POST /api/users {"name": "alice", "password": "super-secret-pw"}
# → ログには password が含まれない
```

nene2 は `url.path` のみをログし、ボディも Cookie も Authorization ヘッダーも記録しない。
Django の `request_finished` シグナルや Flask-Login のデフォルト設定で
機密情報がログに漏洩するケースと対照的に、nene2 はデフォルトで安全。

### クエリパラメーターをログしない ✅

```
GET /api/users?secret_token=hidden
```

`url.path` は `/api/users` のみを返すため、クエリパラメーターはログに含まれない。
URLにAPIキーを含める（推奨されないが）パターンでも機密情報が漏洩しない。

---

## 発見した問題

### 問題1: extra_context が静的のみ — リクエストごとの動的コンテキストが追加できない

```python
# 現状: アプリ起動時の静的な値のみ
app.add_middleware(
    RequestLoggingMiddleware,
    extra_context={"service": "my-api", "version": "1.0.0"},
)
```

```python
# 欲しいが実現できない: リクエストごとの動的な値
# → JWT から取り出した user_id をログに含めたい
# → テナントIDをログに含めたい
app.add_middleware(
    RequestLoggingMiddleware,
    context_extractor=lambda request: {"user_id": get_user_id(request)},  # 非対応
)
```

`structlog.contextvars.bind_contextvars()` を直接使えば可能だが、
その場合はミドルウェアを自作する必要がある。

### 問題2: デバッグ時のリクエストボディログ方法が不明

本番では不要だが、開発時にリクエストボディをログしたいケースがある。
現状では nene2 でこれを行う方法がなく、
カスタムミドルウェアを追加するか `add_route_logging` のようなデコレーターを自作する必要がある。

### 問題3: configure_for_testing() を使わないと caplog でキャプチャできない

```python
# conftest.py に必須
from nene2.log import configure_for_testing
configure_for_testing()
```

この設定を忘れると `caplog` で nene2 のログがキャプチャできず、
「テストしてるのにログが出ない」という混乱を招く。
ドキュメントへの明示が必要。

---

## テスト結果（全14件パス）

```
test_request_received_logged            PASSED
test_request_completed_logged           PASSED
test_method_and_path_in_log             PASSED
test_status_code_in_completed_log       PASSED
test_duration_in_completed_log          PASSED
test_extra_context_in_log               PASSED
test_health_not_logged                  PASSED
test_request_body_not_in_log            PASSED
test_request_query_params_in_nene2_log  PASSED  # nene2はクエリを含まない ✅
test_error_request_still_logged         PASSED
test_error_request_has_status_500       PASSED
test_friction_no_request_body_logging_api  PASSED
test_friction_no_response_body_logging  PASSED
test_friction_no_user_id_in_log_without_custom_context  PASSED
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F79-1 | extra_context が静的のみ — リクエストごとの動的コンテキスト（user_id等）が追加できない | 中 |
| F79-2 | デバッグ用のリクエストボディログ方法がない | 低 |
| F79-3 | configure_for_testing() 未設定だと caplog でログがキャプチャできない | 中 |

---

## 使用感（主観評価）

### 直感性 ★★★★★

`setup_middlewares(app)` で自動的にリクエストログが有効になるのは非常に快適。
`extra_context` で追加フィールドを注入できる設計もわかりやすい。
`exclude_paths` でヘルスチェックを除外できるのも実務的。

### 実害の深刻さ ★★☆☆☆

機密情報をログしないデフォルト設計は本番環境で非常に重要で、これは大きな強み。
`configure_for_testing()` の存在を知らないと pytest で詰まるが、
ドキュメントに追記すれば解決する軽い問題。

### 修正のしやすさ ★★★★☆

動的コンテキストの追加は `context_extractor` コールバックを追加すれば実現できる。
実装は `dispatch()` 内で `context_extractor(request)` を呼んで結果を `bind_contextvars()` に渡すだけ。

### 総合コメント

RequestLoggingMiddleware は実用的でセキュリティ設計も適切。
`configure_for_testing()` のドキュメント強化と、
`context_extractor` パラメーターの追加でさらに実用性が高まる。
全体的に「使っていて気持ちいい」ミドルウェア。

---

## 推奨アクション

1. **Issue**: `RequestLoggingMiddleware` に `context_extractor` コールバックパラメーターを追加
2. **Issue**: `configure_for_testing()` の使い方を README のテストセクションに追記
