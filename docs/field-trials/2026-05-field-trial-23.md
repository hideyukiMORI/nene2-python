# FT23: RequestSizeLimitMiddleware 実運用検証

**日付**: 2026-05-20
**テーマ**: `RequestSizeLimitMiddleware` を使った大容量リクエスト拒否の実運用検証
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft23-size-limit/`

---

## 目的

`nene2.middleware.RequestSizeLimitMiddleware` をドキュメントアップロード API に組み込み、
サイズ制限の動作確認と摩擦点を発見する。

---

## 実施内容

- `max_bytes=1024`（1KB）の制限を設定した API を作成
- `/upload/large` を `exclude_paths` で除外（大容量ファイル用）
- 通常の JSON エンドポイント (`/api/note`) と小容量アップロード (`/upload/small`) でテスト

---

## テスト結果

### test_app.py（正常系・機能確認）
| テスト | 結果 |
|---|---|
| test_small_request_passes | PASS |
| test_large_request_to_normal_endpoint_returns_413 | PASS |
| test_excluded_path_accepts_large_request | PASS |
| test_small_upload_to_non_excluded_endpoint_passes | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_no_per_path_size_limits | PASS | あり |
| test_413_response_does_not_include_max_bytes_in_structured_field | PASS | あり |
| test_content_length_header_absent_still_checked | PASS | なし（正しい動作） |

---

## 発見した摩擦点

### FT23-F1: エンドポイントごとに異なるサイズ制限を設定できない

**概要**: ThrottleMiddleware と同じ問題。全エンドポイントに同一の `max_bytes` しか設定できない。

**判断**: FT20 の ThrottleMiddleware と同様の問題で、別 Issue (#222) として既存。
今回は重複 Issue を作成しない。

---

### FT23-F2: 413 レスポンスの制限値が構造化フィールドで返されない

**概要**: 413 応答の `detail` フィールドに "Request body must not exceed 1024 bytes." と
テキストで含まれるが、`max_bytes: 1024` のような構造化フィールドがない。

**影響**: クライアント SDK が制限値を機械的に読み取れない。
人間が読むログやエラーメッセージには十分だが、プログラム的な利用が難しい。

**期待する解決策**: `_too_large()` レスポンスに `extra={"max_bytes": self._max_bytes}` を追加。

---

### FT23-F3: Content-Length なしでも body チェックが動作する（摩擦なし）

チャンクエンコードで Content-Length ヘッダーがない場合でも、
実際の body を読んでサイズチェックするため、バイパスできない。これは正しい動作。

---

## まとめ

`RequestSizeLimitMiddleware` の基本機能（Content-Length チェック、body チェック、
`exclude_paths`、413 Problem Details 応答）は問題なく動作する。

摩擦点:
1. **413 レスポンスに max_bytes 構造化フィールドがない** → Issue 化・修正対象
2. **パスごとのサイズ制限が不可** → 既存 Issue (#222) と共通問題
