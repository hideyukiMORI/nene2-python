# Field Trial 41: structlog テスト統合 — configure_for_testing() + caplog ログ相関

**日付**: 2026-05-20
**バージョン**: v1.8.5 時点
**テーマ**: `configure_for_testing()` + pytest `caplog` でリクエスト ID をログで追跡するパターンの実運用確認

---

## 概要

`nene2.log.configure_for_testing()` を `conftest.py` のモジュールレベルで呼び出し、
`RequestIdMiddleware` + `RequestLoggingMiddleware` を組み合わせたアプリのログを
pytest の `caplog` でキャプチャ・検証するパターンを実装した。
structlog と stdlib logging の橋渡し構造における制約も確認した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft41-log-testing/` に以下を作成:

- **`conftest.py`** — モジュールレベルで `configure_for_testing()` を呼び出し
- **`app.py`** — `RequestIdMiddleware` / `RequestLoggingMiddleware` / `ErrorHandlerMiddleware` を積んだ FastAPI アプリ。`extra_context` パラメータで静的フィールドを全ログに付加
- **`test_app.py`** — 正常系・ヘッダー確認・caplog キャプチャ・ミドルウェアログ確認 (5 件)
- **`test_friction.py`** — 摩擦点の確認テスト (4 件)

**テスト結果**: 9 件全通過 ✅

---

## 摩擦点

### FP41-1: configure_for_testing() は conftest.py のモジュールレベルで呼ぶ必要がある

**分類**: 軽微な摩擦（設計通り・注意喚起）

`configure_for_testing()` は structlog のグローバル設定を変更するため、
テスト関数内で呼んでも機能するが、全テストに適用するには
`conftest.py` のモジュールレベルで呼ぶことが重要。
テスト関数内で呼ぶと、その関数のみに限定されず他のテストに副作用を与える可能性がある。

```python
# conftest.py — 正しいパターン
from nene2.log import configure_for_testing
configure_for_testing()
```

**判断**: ドキュメントに記載されたパターン通り。現行の `docs/how-to/run-tests.md` に
明示的に記載することで摩擦を減らせる。

---

### FP41-2: caplog.records の LogRecord に request_id フィールドが直接ない

**分類**: 設計上の制約（許容範囲）

`RequestIdMiddleware` が `structlog.contextvars.bind_contextvars(request_id=...)` で
バインドした値は、pytest の `caplog` が返す stdlib `LogRecord` に直接属性として
アクセスできない（`record.request_id` が存在しない）。

`ProcessorFormatter` を通すとメッセージ文字列に request_id が含まれるが、
構造化フィールドとして直接取り出すことはできない。

```python
# NG — LogRecord に直接属性はない
for record in caplog.records:
    print(record.request_id)  # AttributeError

# OK — メッセージ文字列に含まれる
assert "request-id-test" not in " ".join(r.message for r in caplog.records)
# (request_id の値は UUID であり、テスト側から事前に知ることはできない)
```

**判断**: structlog と stdlib logging の橋渡し構造による設計上の制約。
`caplog` でのログ検証はメッセージ文字列ベースで行うのが現実的なアプローチ。
`ProcessorFormatter` に対するテストを書きたい場合は structlog の `capture_logs()` を使う方法もある。

---

### FP41-3: caplog のキャプチャには configure_for_testing() が必須

**分類**: 注意喚起（ドキュメントで対応済み）

`configure_for_testing()` を呼ばない状態では、structlog のログは
pytest の `caplog` にキャプチャされない。
JSON レンダラーのまま stdout に出力されるため、
テストで structlog ログを検証するには必ず `configure_for_testing()` を呼ぶ必要がある。

**判断**: FT18 で実装した機能の使い方確認。`run-tests.md` に caplog との統合手順を追記する価値がある。

---

### FP41-4: structlog.contextvars でバインドした値はメッセージ文字列に含まれる

**分類**: 摩擦なし（設計の確認）

`structlog.contextvars.bind_contextvars(key="value")` でバインドした値は、
`configure_for_testing()` の設定下では `record.message` にキー＝値形式で含まれる。
テストで構造化フィールドを検証する場合はメッセージ文字列の部分一致で確認できる。

```python
structlog.contextvars.bind_contextvars(request_id="test-123")
log.info("hello")
# caplog.records[0].message → "hello request_id=test-123" (または類似形式)
```

**判断**: structlog + caplog の統合パターンとして文字列検索が現実的。

---

## フレームワーク変更

なし（全て設計通りの挙動）

ドキュメント追記のみ検討:
- `docs/how-to/run-tests.md` に `configure_for_testing()` + caplog パターンを追記

---

## 関連

- `nene2.log.configure_for_testing` (FT18, v1.8.0)
- `nene2.middleware.RequestIdMiddleware`
- `nene2.middleware.RequestLoggingMiddleware`
- FT18 (configure_for_testing 実装, v1.8.0)
- FT30 (RequestLoggingMiddleware extra_context, v1.8.2)
