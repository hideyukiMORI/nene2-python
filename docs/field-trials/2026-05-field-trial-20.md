# FT20: ThrottleMiddleware 実運用検証

**日付**: 2026-05-20
**テーマ**: `ThrottleMiddleware` を使ったレート制限 API の実運用検証
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft20-throttle/`

---

## 目的

`nene2.middleware.ThrottleMiddleware` を実際のアプリ（公開 API + ヘルスチェック）に組み込み、
レート制限の動作確認と摩擦点を発見する。

---

## 実施内容

- `limit=3, window=60` のレート制限を設定した FastAPI アプリを作成
- `/health` を `exclude_paths` で除外
- `/api/data`、`/api/expensive` の 2 エンドポイントにレート制限を適用

---

## テスト結果

### test_app.py（正常系・機能確認）
| テスト | 結果 |
|---|---|
| test_health_check_is_not_rate_limited | PASS |
| test_requests_within_limit_succeed | PASS |
| test_requests_exceeding_limit_return_429 | PASS |
| test_rate_limit_429_includes_retry_after_header | PASS |
| test_rate_limit_applies_across_different_endpoints | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_no_rate_limit_headers_on_successful_responses | PASS | あり |
| test_no_per_path_rate_limits | PASS | あり |
| test_memory_not_cleaned_up_over_time | PASS | あり |

---

## 発見した摩擦点

### FT20-F1: 通常レスポンスに X-RateLimit-* ヘッダーが付かない

**概要**: 429 応答には `Retry-After` ヘッダーが付くが、
通常のレスポンスには `X-RateLimit-Limit`、`X-RateLimit-Remaining`、`X-RateLimit-Reset`
が付かない。

**影響**: クライアントが自分のレート制限状況をリアルタイムで把握できない。
SDK やクライアントが事前にスロットリングする「adaptive throttling」が実装できない。

**期待する解決策**: 全レスポンスに `X-RateLimit-*` ヘッダーを付与するオプションを追加。

---

### FT20-F2: エンドポイントごとに異なるレート制限を設定できない

**概要**: `ThrottleMiddleware` は全エンドポイントで同一の `limit`/`window` のみ対応。
コスト大きなエンドポイント（`/api/expensive`: 10req/min）と軽いエンドポイント
（`/api/data`: 100req/min）で異なる制限を設定できない。

**影響**: 実運用では計算コストの重いエンドポイントを個別に絞りたいケースが多い。

**期待する解決策**: `path_limits: dict[str, int] | None = None` のようなパスごとの
レート制限設定パラメータを追加。

---

### FT20-F3: 古い IP エントリがメモリから削除されない

**概要**: `_counts` dict のエントリは、ウィンドウ経過後もメモリに残り続ける。
リクエスト時に古いエントリを上書きするだけで、削除はしない設計。

**影響**: 長時間稼働するサーバーでユニーク IP が多い場合、メモリが増加し続ける。

**期待する解決策**: ウィンドウ経過後の古いエントリを定期的に削除する
クリーンアップ機構（ローリングクリーンアップや LRU キャッシュ制限など）を追加。

---

## まとめ

`ThrottleMiddleware` の基本機能（IP ベースの固定ウィンドウレート制限、429 応答、
`Retry-After` ヘッダー、`exclude_paths`）は問題なく動作する。
実運用でよく必要になる以下の 3 点が摩擦として発見された:

1. **`X-RateLimit-*` ヘッダーの欠如** → クライアントが制限状況を把握できない
2. **パスごとのレート制限が不可** → 計算コストの差があるエンドポイントの制御が難しい
3. **古いエントリのメモリ残留** → 長時間稼働時のメモリリーク懸念

F1 (X-RateLimit headers) が最も実装インパクトが高く、今回の修正対象とする。
