# FT239: statistics — mean / median / stdev / quantiles

**日付**: 2026-05-29
**テーマ**: Python `statistics` モジュールの統計量算出の実装と検証
**セキュリティ診断**: なし（239 % 3 = 2）
**クラッカーペンテスト**: なし（239 % 4 = 3）

---

## 概要

`statistics` は平均・中央値・標準偏差・分位数などの基本統計量を提供する。HTTP API でラップし数値リストの要約統計と四分位数を検証した。`StatisticsError`（空・標本数不足）の扱いとデータ点数上限が観察ポイント。

| API | ユースケース |
|---|---|
| `statistics.mean` / `median` | 平均・中央値 |
| `statistics.stdev` | 標本標準偏差（n>=2 必須） |
| `statistics.quantiles(data, n=4)` | 四分位数 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft239-statistics/`

| 関数 | 概要 |
|---|---|
| `summarize()` | count/mean/median/stdev(n>=2)/min/max |
| `quartiles()` | `quantiles(n=4)` |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/stats/summary` | 基本統計量 |
| POST | `/stats/quartiles` | 四分位数 |

---

## 摩擦点

### F-1: `stdev` は n>=2、空データは `StatisticsError`

**観察**: `statistics.stdev` は標本標準偏差で**2 点以上が必須**（n<2 で `StatisticsError`）。空リストは `mean` でも `StatisticsError`。ユーザー入力をそのまま渡すと例外になる。

**対処**: 空は事前に 422、stdev は n>=2 のときのみ算出し n<2 では `None` を返す（`stdev: float | None`）。四分位数も n<2 を 422。

### F-2: 点数上限で DoS を防ぐ

**観察**: 巨大なデータ点列を渡すと計算コスト・メモリが増す。`statistics` 自体に上限はない。

**対処**: `MAX_POINTS = 10_000` と Pydantic `max_length=10_000` で二重制限。

### F-3: 浮動小数の丸め

**観察**: 統計量は浮動小数で誤差が出る（`mean([0.1,0.2])` 等）。JSON 出力で長い小数になり比較しづらい。

**対処**: 結果を 6 桁に丸めて返す（`round(x, 6)`）。厳密性が要る用途は `Fraction` 入力や `fmean` を検討。

---

## テスト結果

```
6 passed in 0.84s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

平均・中央値は身近。stdev が「2 点以上必要」なのは意外だが None で返るので扱いやすい。

**ドキュメント理解**: 標本標準偏差と母標準偏差（pstdev）の違いは補足が要る。
**事故リスク（低）**: 計算のみ。
**規約の使いやすさ**: data → summary が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

メトリクス集計やレポートで使う。空リスト・1 点での例外は実務で踏みやすい。

**コピペ可能性**: summarize は流用可。
**拡張時の罠**: StatisticsError・stdev の標本/母の区別。
**事故リスク（低）**: 事前検証あり。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS には標準統計がないのでサーバー側算出は便利。

**エラーレスポンスの質**: 空・点数超過は 422。
**Python 固有概念**: stdev(標本) vs pstdev(母)。
**事故リスク（低）**: 上限あり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

大規模データは numpy/pandas が適。標準 `statistics` は小規模・依存を増やしたくない場面向け。

**他フレームワークとの差異**: numpy は高速だが依存追加。statistics は標準で十分な規模に。
**nene2 の薄さへの評価**: 薄いラップとして妥当。点数上限が適切。
**事故リスク（低）**: 上限・例外処理あり。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- 空・n<2 の `StatisticsError` を事前検証で防いでいるか。
- 標本標準偏差（stdev）と母標準偏差（pstdev）を取り違えていないか。
- データ点数に上限があるか（DoS）。
- 浮動小数の丸め・精度要件。

**チームでの安全なパターン**: 大規模は numpy、軽量は statistics。例外は事前検証で 422 に。
**事故リスク（低）**: 例外・上限を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 件数制限・`ValidationException` 変換・`logging` 使用は準拠。`stdev: float | None` の Optional 表現も型明示的。
**初心者でも安全な API 達成度**: 空・n<2 を事前に弾き、stdev を None で表現し例外の余地を排除。
**改善提案**: 標本/母標準偏差の選択や `fmean`/`Fraction` 精度オプションを要件に応じ how-to に補足する。
