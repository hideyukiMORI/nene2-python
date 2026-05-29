# FT281: math — isclose / gcd / factorial（過大入力ガード）

**日付**: 2026-05-29
**テーマ**: Python `math` モジュールの数値演算の実装と検証
**セキュリティ診断**: なし（281 % 3 = 2）
**クラッカーペンテスト**: なし（281 % 4 = 1）

---

## 概要

`math` は数学関数を提供する。HTTP API でラップし gcd / factorial / isclose を検証した。`factorial` の過大入力による**巨大整数 DoS**と、`isclose` の浮動小数比較が要点。

| API | ユースケース |
|---|---|
| `math.gcd(*ints)` | 最大公約数（複数引数） |
| `math.factorial(n)` | 階乗（巨大整数に注意） |
| `math.isclose(a, b, rel_tol, abs_tol)` | 浮動小数の近似比較 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft281-math/`

| 関数 | 概要 |
|---|---|
| `gcd_of()` | 整数列の gcd |
| `factorial_of()` | n を上限化し桁数 + 文字列で返す |
| `is_close()` | isfinite チェック + rel/abs_tol |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/math/gcd` | 最大公約数 |
| POST | `/math/factorial` | 階乗（上限付き） |
| POST | `/math/isclose` | 近似比較 |

---

## 摩擦点

### F-1: `factorial` の過大入力は巨大整数 DoS

**観察**: `math.factorial(100000)` は数十万桁の整数を生成し CPU・メモリを消費、`str()` 変換も Python の int 桁数制限に当たる。ユーザー入力をそのまま渡すと DoS。

**対処**: `n` を 1000 に上限化。結果は桁数 + 文字列で返す（巨大数をそのまま JSON に乗せない）。`n=10000` を 422。

### F-2: `isclose` は浮動小数比較の正解（`==` を避ける）

**観察**: `0.1 + 0.2 == 0.3` は False（浮動小数誤差）。`math.isclose` で許容誤差付き比較が正解。ただし **0 付近では rel_tol が効かない**ため `abs_tol` が必要。

**対処**: rel_tol（既定 1e-9）+ abs_tol を受ける。`0.1+0.2` ≈ `0.3` を True、0 付近は abs_tol で判定。

### F-3: NaN/Infinity と負の許容誤差

**観察**: `isclose(nan, nan)` は False、inf を渡すと予期せぬ結果。負の tol は無意味。

**対処**: `isfinite` チェックで inf/nan を 422、tol の非負を検証。

---

## テスト結果

```
8 passed in 0.85s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`0.1+0.2 != 0.3` の解決に isclose が使えると学べる。階乗の桁爆発も体感できる。

**ドキュメント理解**: abs_tol の必要性をコメントで明示。
**事故リスク（低）**: 計算のみ。
**規約の使いやすさ**: 各エンドポイントが明快。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

数値処理で float の == 比較をやりがち。isclose へ移行すべき。factorial の上限も実務で必要。

**コピペ可能性**: is_close/factorial_of は流用可。
**拡張時の罠**: factorial の桁爆発・0 付近の rel_tol。
**事故リスク（低）**: 上限・isfinite あり。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS の `Number.EPSILON` 比較に対応。浮動小数の罠は共通。

**エラーレスポンスの質**: 過大 n・inf は 422。
**Python 固有概念**: 任意精度 int・桁数制限。
**事故リスク（低）**: 上限あり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

float 比較は isclose、金額は decimal（FT250）。factorial の桁爆発は int 桁数制限（3.11+）とも関連。

**他フレームワークとの差異**: 大差なし。
**nene2 の薄さへの評価**: 上限・isfinite・abs_tol が丁寧。
**事故リスク（低）**: 上限あり。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- float を `==` で比較していないか（isclose、0 付近は abs_tol）。
- factorial 等の入力に上限があるか（巨大整数 DoS）。
- isfinite で inf/nan を弾いているか。
- 巨大数をそのまま JSON に乗せていないか（桁数 + 文字列）。

**チームでの安全なパターン**: float 比較は isclose、巨大計算は上限、金額は decimal。
**事故リスク（低）**: 上限を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 範囲制限・`ValidationException` 変換・`logging` 使用は準拠。FT250（decimal）/FT252（json 整数桁）/FT275（cmath isfinite）と一貫。
**初心者でも安全な API 達成度**: 上限・isfinite・abs_tol を関数内に固定。
**改善提案**: 数値共通の「isfinite + 範囲 + 巨大整数桁制限」バリデータを `nene2` に集約する。
