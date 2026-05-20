# FT62: RequestLoggingMiddleware 実運用検証

**日付**: 2026-05-20  
**テーマ**: リクエストロギングミドルウェア (`RequestLoggingMiddleware`) の実運用確認  
**バージョン**: v1.8.15  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft62-request-logging/`

---

## 概要

`nene2.middleware.RequestLoggingMiddleware` を FastAPI に組み込み、
structlog コンテキスト変数の設定・除外パス・extra_context・RequestIdMiddleware との連携を検証した。

---

## 実装内容

- `RequestLoggingMiddleware(exclude_paths=["/health"])`: ヘルスチェックをログ除外
- `extra_context={"service": "ft62"}`: リクエストログへのカスタムフィールド追加
- `RequestIdMiddleware` と組み合わせてリクエストIDのログへの自動バインド
- structlog プロセッサをカスタマイズしてログ出力をキャプチャして確認

---

## テスト結果

**6/6 passed**

| テスト | 結果 |
|---|---|
| `test_request_passes_through_logging_middleware` | PASSED |
| `test_excluded_path_still_returns_200` | PASSED |
| `test_non_excluded_path_passes_normally` | PASSED |
| `test_extra_context_does_not_break_requests` | PASSED |
| `test_structlog_context_vars_populated_during_request` | PASSED |
| `test_logging_middleware_with_request_id_middleware` | PASSED |

---

## Friction Points

なし。`RequestLoggingMiddleware` はすべての機能が直感的に動作した。

**特筆点**:
- structlog の `merge_contextvars` プロセッサで、ミドルウェアがバインドしたコンテキストが
  アプリコード側のログにも自動で引き継がれる設計が強力
- `RequestIdMiddleware` と組み合わせると `request_id` がすべてのログに自動付与される
- `configure_for_testing()` を使うと structlog の設定がテスト向けに上書きされるため、
  structlog のカスタムプロセッサをテスト内で設定しなおす必要がある点は把握が必要

---

## 結論

`RequestLoggingMiddleware` は実運用で問題なく使用できる。
`RequestIdMiddleware` と組み合わせて使うのが推奨パターン。
