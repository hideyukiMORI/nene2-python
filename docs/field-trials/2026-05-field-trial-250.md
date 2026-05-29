# FT250: decimal — Decimal / 精度 / 丸めモード（金額計算）

**日付**: 2026-05-29
**テーマ**: Python `decimal` モジュールの正確な十進演算の実装と検証
**セキュリティ診断**: なし（250 % 3 = 1）
**クラッカーペンテスト**: なし（250 % 4 = 2）

---

## 概要

`decimal` は十進浮動小数点で**金額計算に必須の精度**を提供する。HTTP API でラップし合計・除算を検証した。最大の要点は **入力を文字列で受ける**こと — `Decimal(0.1)`（float 経由）は誤差を持つが `Decimal("0.1")` は厳密に 0.1。

| API | ユースケース |
|---|---|
| `Decimal("0.1")` | 文字列から厳密生成 |
| `.quantize(Decimal("0.01"), rounding=...)` | 桁丸め |
| `ROUND_HALF_UP` / `ROUND_HALF_EVEN` | 丸めモード |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft250-decimal/`

| 関数 | 概要 |
|---|---|
| `sum_amounts()` | 金額文字列を厳密合計し 2 桁に丸め |
| `divide_amount()` | 丸めモード指定で除算 |
| `_to_decimal()` | 文字列から生成、NaN/Infinity を拒否 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/decimal/sum` | 金額を厳密に合計 |
| POST | `/decimal/divide` | 丸めモード指定で除算 |

---

## 摩擦点

### F-1: 入力は文字列で受ける（float 経由の Decimal は誤差を持つ）

**観察**: `Decimal(0.1)`（float から）は `0.1000000000000000055511151231257827021181583404541015625` になる。JSON で数値を float として受けると精度が失われる。`0.1 + 0.2` は float で `0.30000000000000004`。

**対処**: 金額は **`str` で受信**し `Decimal("0.1")` で生成。`0.1 + 0.2` → `"0.30"` を確認。Pydantic でも `condecimal` や `Decimal` 型を使えるが、本 FT は明示的に文字列受けで原理を示す。

### F-2: 丸めモードは用途で選ぶ（HALF_UP vs HALF_EVEN）

**観察**: `quantize` のデフォルトは `ROUND_HALF_EVEN`（銀行丸め）。一般的な「四捨五入」は `ROUND_HALF_UP`。誤ると 0.5 の扱いがずれ会計が合わない。

**対処**: 丸めモードを許可リスト（half_up/half_even）で受け、合計は HALF_UP 既定。`eval` で任意の定数を解決しない。

### F-3: NaN / Infinity を拒否

**観察**: `Decimal("NaN")` / `Decimal("Infinity")` は有効な Decimal だが、金額としては不正。これを通すと集計が壊れる。

**対処**: `is_finite()` で NaN/Infinity を 422。不正文字列は `InvalidOperation` 捕捉で 422。

---

## テスト結果

```
9 passed in 0.91s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`0.1+0.2` が float で `0.30000...4` になるのは衝撃。Decimal で厳密になるのが分かりやすい。

**ドキュメント理解**: 文字列受けの理由をコメントで明示。
**事故リスク（中）**: 金額を float で扱う。
**規約の使いやすさ**: amounts（文字列配列）が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

会計・課金で float を使う事故が多い。文字列受け + Decimal が定石。

**コピペ可能性**: sum/divide は流用可。
**拡張時の罠**: float 経由 Decimal・丸めモードの既定（HALF_EVEN）。
**事故リスク（中）**: 丸め誤り。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS の Number 精度問題（同じ）に対応。金額は文字列 or 整数（最小単位）で扱う発想が共通。

**エラーレスポンスの質**: 不正・NaN は 422。
**Python 固有概念**: Decimal・quantize・丸めモード。
**事故リスク（低）**: 文字列受け。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

金額は Decimal か整数（cents）。DB も DECIMAL 型。丸めモードを明示する規律が重要。

**他フレームワークとの差異**: DRF の DecimalField も文字列シリアライズ。
**nene2 の薄さへの評価**: 文字列受け・NaN 拒否・丸め許可リストが適切。
**事故リスク（低）**: 原理に沿った設計。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- 金額を float で扱っていないか（文字列/Decimal/整数 cents）。
- 丸めモードを明示しているか（既定 HALF_EVEN の罠）。
- NaN/Infinity を拒否しているか。
- 通貨ごとの小数桁（JPY=0, USD=2）を考慮しているか。

**チームでの安全なパターン**: 金額は Decimal、入出力は文字列、丸めは明示。
**事故リスク（低）**: NaN/不正/丸めを回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。丸めモードの許可リスト（eval 不使用）も整合。
**初心者でも安全な API 達成度**: 文字列受け・NaN 拒否・丸め許可リストを関数内に固定し、float 誤差・不正値の余地を排除。
**改善提案**: 通貨別小数桁・Pydantic `condecimal` 活用を how-to に補足する。
