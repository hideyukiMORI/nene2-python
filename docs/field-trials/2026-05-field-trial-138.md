# Field Trial 138: decimal + fractions + statistics の活用

## テーマ

`Decimal` で高精度金融計算、`Fraction` で有理数演算、
`statistics` で統計処理を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft138-decimal-statistics/` に以下を実装:

- `calculate_compound_interest()` — `Decimal` で複利計算（`ROUND_HALF_UP`）
- `calculate_tax()` — 消費税計算（四捨五入、`quantize`）
- `calculate_exchange()` — 外貨換算
- `simplify_ratio()` — `Fraction` で比率を約分
- `compute_stats()` — `statistics.mean/median/mode/stdev/variance` で統計量
- `compute_quantiles()` — `statistics.quantiles` で分位数
- 21 テスト通過（摩擦2件あり）

## テスト結果

初回: 2失敗 → 修正後: 21テスト全通過。

## Friction Points

### FP1: `statistics.stdev` は標本標準偏差（ddof=1）— 母標準偏差ではない

```python
values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
statistics.stdev(values)  # ≈ 2.138 (標本、ddof=1)
statistics.pstdev(values) # = 2.000 (母集団)
```

`statistics.stdev` は標本標準偏差（分母が `n-1`）。
母集団の標準偏差が必要な場合は `statistics.pstdev` を使う。

### FP2: `Decimal(str(float))` で `quantize` しないと表示が `"1100.0"` になる

```python
Decimal(str(1000.0))  # → Decimal("1000.0")
Decimal("100") + Decimal("1000.0")  # → Decimal("1100.0")
```

`float` を `str()` 経由で `Decimal` に変換すると小数部を保持する。
整数と加算しても `"1100.0"` のまま。
金融計算では `quantize(Decimal("0.01"))` で必ず丸めるべき。

## 観察

### O1: `Decimal` で浮動小数点誤差を回避できる

```python
# float の誤差
0.1 + 0.2 == 0.3   # False (0.30000000000000004)

# Decimal なら正確
Decimal("0.1") + Decimal("0.2") == Decimal("0.3")  # True
```

金融計算ではすべての入力を `Decimal(str(float_value))` で変換する。
`Decimal(float_value)` はNG（float の誤差を引き継ぐ）。

### O2: `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` で金融丸めができる

```python
amount = Decimal("100.125")
amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  # 100.13
amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)     # 100
```

`ROUND_HALF_UP` は一般的な「四捨五入」。Python のデフォルトは銀行丸め（ROUND_HALF_EVEN）。
日本の消費税計算は切り捨て（`ROUND_FLOOR`）が正式。

### O3: `Fraction` で分数演算が正確に行える

```python
Fraction(1, 3) + Fraction(1, 6)  # Fraction(1, 2) — 正確に 1/2
Fraction(6, 4)                   # → Fraction(3, 2) — 自動的に約分
```

レシピのスケーリング（3倍にする）や比率計算に `Fraction` は適している。
`float` では `1/3 * 3 = 0.9999...` になる場合がある。

### O4: `statistics.quantiles` でパーセンタイルを計算できる

```python
statistics.quantiles([1, 2, 3, ..., 100], n=4)
# → [Q1, Q2, Q3] (n=4 で四分位数 — 3つの境界)
```

`n=4` は四分位数（3点）、`n=100` はパーセンタイル（99点）。

## まとめ

FT138 は摩擦2件（`stdev` の種類、`quantize` 忘れ）。
`Decimal` による金融計算、`Fraction` による有理数演算、`statistics` による統計処理を
FastAPI エンドポイントで確認した。金融計算は必ず `Decimal(str(...))` + `quantize` を使うべき。
