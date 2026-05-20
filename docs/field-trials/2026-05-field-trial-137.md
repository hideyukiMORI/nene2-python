# Field Trial 137: datetime + zoneinfo の高度な活用

## テーマ

`ZoneInfo` によるタイムゾーン対応日時操作、`timedelta` による営業日計算、
`calendar` によるカレンダー情報取得、`strftime`/`fromisoformat` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft137-datetime-zoneinfo/` に以下を実装:

- `convert_timezone()` — `ZoneInfo` でタイムゾーン変換（naive datetime は UTC 扱い）
- `now_in_timezones()` — 複数タイムゾーンの現在時刻を返す
- `add_business_days()` — `timedelta` で土日をスキップして営業日加算
- `time_until()` — ターゲット日時までの残り時間を `timedelta` で計算
- `get_month_calendar()` — `calendar.monthrange` / `monthcalendar` でカレンダー情報
- `format_datetime()` — `strftime` で複数フォーマット対応
- 各 HTTP エンドポイント
- 22 テスト通過（摩擦1件あり）

## テスト結果

初回: 1失敗 → 修正後: 22テスト全通過。

## Friction Points

### FP1: `ZoneInfo` をコンテキストマネージャーとして使えない

```python
# NG: ZoneInfo はコンテキストマネージャーではない
with ZoneInfo("Asia/Tokyo") as tz:
    ...
# → AttributeError: __exit__

# OK: 直接 ZoneInfo オブジェクトを使う
tz = ZoneInfo("Asia/Tokyo")
dt.astimezone(tz)
```

`pytz` の `timezone` オブジェクトはコンテキストマネージャーだったが、
Python 標準の `zoneinfo.ZoneInfo` はコンテキストマネージャーではない。
混同しやすい落とし穴。

**対処**: `ZoneInfo(tz_name)` をそのまま変数に代入して使う。

## 観察

### O1: `zoneinfo.ZoneInfo` で Python 標準ライブラリのみでタイムゾーン処理できる

```python
from zoneinfo import ZoneInfo
from datetime import UTC, datetime

dt_utc = datetime(2026, 1, 15, 0, 0, 0, tzinfo=UTC)
dt_jst = dt_utc.astimezone(ZoneInfo("Asia/Tokyo"))
# → 2026-01-15T09:00:00+09:00
```

Python 3.9 以降は `pytz` や `dateutil` なしで IANA タイムゾーンが使える。
`tzdata` パッケージをインストールするか OS のタイムゾーンデータが必要。

### O2: `datetime.fromisoformat()` で ISO 8601 文字列をパースできる

```python
# Python 3.11 以降は完全な ISO 8601 に対応
dt = datetime.fromisoformat("2026-01-15T09:00:00+09:00")
dt.utcoffset()  # +09:00
```

Python 3.7〜3.10 では `fromisoformat` が `±HH:MM` のオフセットのみ対応。
Python 3.11 以降で `Z` サフィックスや秒の小数部もサポートされた。

### O3: `calendar.monthrange()` で月の最初の曜日と日数を一度に取得できる

```python
first_weekday, days_in_month = calendar.monthrange(2026, 2)
# first_weekday: 0=月, 1=火, ..., 6=日
# days_in_month: 28
```

### O4: `timedelta` で土日スキップの営業日計算が実装できる

```python
def add_business_days(start: datetime, days: int) -> datetime:
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # 0-4 = 月〜金
            added += 1
    return current
```

祝日は `japanize_matplotlib` 等の外部ライブラリが必要。標準ライブラリのみでは祝日非対応。

## まとめ

FT137 は摩擦1件（`ZoneInfo` のコンテキストマネージャー誤用）。
`zoneinfo` + `datetime` で `pytz` なしにタイムゾーン対応処理が書けることを確認した。
