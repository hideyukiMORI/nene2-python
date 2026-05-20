# Field Trial 55: parse_db_datetime 実運用検証

**Date**: 2026-05-20
**Theme**: `nene2.database.utils.parse_db_datetime` の実運用パターン検証
**Version under test**: v1.8.14
**FT App**: `/home/xi/docker/nene2-python-FT/ft55-parse-datetime/`

---

## 概要

SQLite に DATETIME 値を保存・読み出しし、`parse_db_datetime` で UTC-aware datetime に
変換するパターンをイベント管理 API で実運用した。

---

## 実装内容

```python
from nene2.database.utils import parse_db_datetime

event = Event(
    id=row[0],
    title=row[1],
    scheduled_at=parse_db_datetime(row[2]),  # SQLite 文字列 → UTC-aware datetime
)
```

SQLite は DATETIME を `"2026-06-01 12:00:00"` のような文字列で返すが、
`parse_db_datetime` が透過的に UTC-aware `datetime` に変換する。

---

## テスト結果

7 tests, all passed.

| テスト | 結果 |
|---|---|
| イベント作成・取得 | ✅ |
| UTC-aware datetime で返ること | ✅ |
| SQLite 文字列形式の変換 (`"2026-06-01 12:00:00"`) | ✅ |
| MySQL 形式の naive datetime を UTC-aware に変換 | ✅ |
| すでに timezone-aware な datetime は保持 | ✅ |
| ISO 8601 の T 区切り形式のサポート | ✅ |
| 存在しないイベントで 404 | ✅ |

---

## 摩擦ポイント

摩擦なし。`parse_db_datetime` の API は直感的で、SQLite / MySQL の差異を透過的に吸収する。

---

## フレームワーク変更

なし。

---

## 結論

`parse_db_datetime` は SQLite (文字列) と MySQL (naive datetime) の両方を透過的に処理し、
常に UTC-aware `datetime` を返す。実運用で摩擦なく使える。
