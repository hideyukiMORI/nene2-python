# FT265: zoneinfo — IANA タイムゾーン変換 / ZoneInfo

**日付**: 2026-05-29
**テーマ**: Python `zoneinfo` モジュールのタイムゾーン変換の実装と検証
**セキュリティ診断**: なし（265 % 3 = 1）
**クラッカーペンテスト**: なし（265 % 4 = 1）

---

## 概要

`zoneinfo`（Python 3.9+）は IANA タイムゾーンデータベースを使った正確なタイムゾーン変換（DST 含む）を提供する。HTTP API でラップし日時のタイムゾーン変換を検証した。`datetime`（FT204）と組み合わせる定番。

| API | ユースケース |
|---|---|
| `ZoneInfo("Asia/Tokyo")` | IANA タイムゾーン |
| `dt.astimezone(zone)` | タイムゾーン変換 |
| `zoneinfo.available_timezones()` | 有効な tz 名の集合 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft265-zoneinfo/`

| 関数 | 概要 |
|---|---|
| `convert_timezone()` | ISO 日時を from_tz → to_tz に変換 |
| `_zone()` | tz 名を available_timezones で検証 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/tz/convert` | タイムゾーン変換 |

---

## 摩擦点

### F-1: 不正な tz 名は `available_timezones()` で事前検証

**観察**: `ZoneInfo("Mars/Olympus")` は `ZoneInfoNotFoundError`。ユーザー入力をそのまま渡すと例外になる。

**対処**: 起動時に `available_timezones()` を取得し、メンバーシップで事前検証（不正名は 422）。`ZoneInfoNotFoundError` も捕捉。

### F-2: naive datetime には tzinfo を付与する

**観察**: `datetime.fromisoformat("2024-01-01T12:00:00")` は naive（tzinfo なし）。これを `astimezone` する前に from_tz を付与しないと、ローカル時刻として誤解釈される。

**対処**: naive なら `replace(tzinfo=from_zone)` で from_tz を付与、aware ならそのまま。その後 `astimezone(to_zone)`。

### F-3: DST（夏時間）は自動処理される

**観察**: `zoneinfo` は IANA DB に基づき DST を自動適用する。同じ `America/New_York` でも 1 月は EST(-05:00)、7 月は EDT(-04:00)。固定オフセットでハードコードすると DST でずれる。

**対処**: `ZoneInfo` に委譲し DST を自動処理。7 月の NY が -04:00、冬が -05:00 を確認。

---

## テスト結果

```
5 passed in 0.96s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

タイムゾーン変換は身近。DST が自動なのは安心。naive/aware の違いは難しい。

**ドキュメント理解**: naive への tzinfo 付与をコメントで明示。
**事故リスク（中）**: naive datetime をそのまま変換して誤解釈。
**規約の使いやすさ**: iso + from/to が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

予約・ログのタイムゾーン処理で使う。固定オフセットのハードコードで DST バグを作りやすい。

**コピペ可能性**: convert_timezone は流用可。
**拡張時の罠**: naive/aware・固定オフセット。
**事故リスク（中）**: DST ずれ。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`Intl.DateTimeFormat` / Temporal に対応。IANA tz 名は共通。

**エラーレスポンスの質**: 不正 tz/日時は 422。
**Python 固有概念**: naive/aware datetime。
**事故リスク（低）**: 検証あり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

保存は UTC、表示時に変換が定石。`zoneinfo` は pytz より新しく推奨（pytz の localize の罠がない）。

**他フレームワークとの差異**: pytz より zoneinfo が安全（fold 対応）。
**nene2 の薄さへの評価**: tz 検証 + naive 付与が丁寧。
**事故リスク（低）**: DST 自動・検証あり。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- 保存は UTC（aware）、変換は表示時か。
- naive datetime を tzinfo なしで変換していないか。
- 固定オフセットをハードコードしていないか（DST）。
- tz 名を検証しているか（不正名の例外）。
- 曖昧な時刻（DST 切替時の fold）の扱い。

**チームでの安全なパターン**: 内部は UTC aware、境界で zoneinfo 変換、tz 名は検証。
**事故リスク（低）**: DST・検証を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。FT204（datetime）と一貫。
**初心者でも安全な API 達成度**: tz 検証・naive 付与・DST 自動を関数内に隠蔽。
**改善提案**: 「保存は UTC aware・変換は zoneinfo・pytz は使わない」を how-to に明記し FT204 と相互リンクする。
