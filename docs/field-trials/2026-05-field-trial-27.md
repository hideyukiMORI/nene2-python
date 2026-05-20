# FT27: ThrottleMiddleware 長時間運用検証

**日付**: 2026-05-20
**テーマ**: `ThrottleMiddleware` の長時間稼働時のメモリ蓄積問題を検証
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft27-throttle-cleanup/`

---

## 目的

`ThrottleMiddleware` の `_counts` ディクショナリに古いエントリが蓄積する問題（Issue #223）を実証し、
修正方針を検討する。

---

## 実施内容

- 複数 IP からのリクエストシミュレーション
- ウィンドウ経過後のエントリ残存を確認
- クリーンアップ機能の有無を検証

---

## テスト結果

### test_app.py（正常系・機能確認）
| テスト | 結果 |
|---|---|
| test_ping_returns_200 | PASS |
| test_rate_limit_headers_present | PASS |
| test_rate_limit_exceeded_returns_429 | PASS |
| test_different_ips_have_separate_counters | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_stale_entries_accumulate_in_memory | PASS | あり（バグ） |
| test_no_cleanup_method_exists_on_throttle_middleware | PASS | あり |

---

## 発見した摩擦点

### FT27-F1: 古いエントリが _counts から削除されない（Issue #223）

**概要**: 異なるクライアント IP からリクエストが来るたびに `_counts` にエントリが追加されるが、
ウィンドウ期間が過ぎても古いエントリは削除されない。
長時間稼働・多数の異なるクライアントが存在する環境ではメモリが際限なく増加する。

**確認した動作**:
```python
# 10 IP のエントリを作成 → window (1秒) 経過後も 10 エントリが残る
# 新しい IP のリクエスト後も 11 エントリ (10 古い + 1 新しい)
```

**修正方針**: `_check_rate()` 内で定期的にクリーンアップを実施する。
`_last_cleanup` タイムスタンプを持ち、`window` 秒経過したときに期限切れエントリを一括削除する。

---

## まとめ

`ThrottleMiddleware` の基本機能は正常に動作する。

摩擦点:
1. **古いエントリのメモリ蓄積** → Issue #223 として登録済み、修正対象
