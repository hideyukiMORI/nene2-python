# FT28: ThrottleMiddleware パスごとのレート制限検証

**日付**: 2026-05-20
**テーマ**: `ThrottleMiddleware` のパスごとのレート制限（Issue #222）
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft28-path-throttle/`

---

## 目的

重いエンドポイントだけ厳しいレート制限をかけたい実運用ニーズを検証する。

---

## 実施内容

- `path_limits` パラメータの不在を確認
- 現状では全エンドポイントで同じ `limit`/`window` しか設定できないことを実証

---

## テスト結果

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_throttle_middleware_does_not_support_path_limits | PASS | あり |
| test_workaround_requires_multiple_middlewares | PASS | あり |

---

## 発見した摩擦点

### FT28-F1: ThrottleMiddleware がパスごとのレート制限をサポートしない（Issue #222）

**概要**: 全エンドポイントで同じ `limit`/`window` しか設定できない。
`/api/expensive` だけ `limit=10` にして残りは `limit=100` にする、という設定ができない。

**期待する使い方**:
```python
app.add_middleware(
    ThrottleMiddleware,
    limit=100,
    window=60,
    path_limits={"/api/expensive": 10, "/api/search": 30},
)
```

---

## まとめ

摩擦点:
1. **`path_limits` 未対応** → Issue #222 として登録済み、修正対象
