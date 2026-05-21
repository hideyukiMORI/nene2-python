# FT176: decimal モジュール

**日付**: 2026-05-21
**テーマ**: `decimal.Decimal` による精度の高い十進数演算・金融計算・丸め制御
**セキュリティ診断**: なし（FT177 で実施）
**クラッカーペンテスト**: **あり**（FT176: 172 + 4 = 176）

---

## 概要

Python 標準ライブラリの `decimal` モジュールを検証する。
`float` の浮動小数点誤差（`0.1 + 0.2 != 0.3`）を回避し、
金融計算で必要な「正確な十進数演算」を `Decimal` 型で実装する。

このFTで確認する点:
- `float` と `Decimal` の精度差（`0.1 + 0.2 == 0.3` の違い）
- `quantize()` による丸めモードの制御（ROUND_HALF_UP, ROUND_HALF_EVEN 等）
- 税計算・割引計算・割り勘といった金融計算パターン
- `Infinity`, `NaN`, 空文字列等の不正入力への防御
- `parse_decimal_safe()` によるバリデーション（`is_finite()` によるInf/NaN ブロック）

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft176-decimal/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `decimal_add/sub/mul/div(a, b)` | 基本四則演算（ゼロ除算は `None`） |
| `round_decimal(value, places, mode)` | 指定モードで丸める |
| `truncate_decimal(value, places)` | `ROUND_FLOOR` で切り捨て |
| `ceil_decimal(value, places)` | `ROUND_CEILING` で切り上げ |
| `ROUNDING_MODES` | 6種の丸めモード辞書 |
| `calculate_tax(price, tax_rate)` | 税計算（ROUND_HALF_UP） |
| `calculate_discount(price, discount_percent)` | 割引計算 |
| `split_bill(total, num_people)` | 割り勘（ROUND_CEILING）|
| `float_precision_demo()` | float vs Decimal 精度比較 |
| `parse_decimal_safe(value)` | Infinity/NaN/長すぎる文字列をブロック |
| `is_valid_decimal(value)` | バリデーション bool |
| `compare_decimals(a, b)` | 大小比較（-1/0/1） |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/decimal/add` | 加算 |
| POST | `/decimal/sub` | 減算 |
| POST | `/decimal/mul` | 乗算 |
| POST | `/decimal/div` | 除算（ゼロ除算 422） |
| POST | `/decimal/round` | 丸め（truncated, ceiling も返す） |
| POST | `/decimal/tax` | 税計算 |
| POST | `/decimal/discount` | 割引計算 |
| POST | `/decimal/split-bill` | 割り勘 |
| GET | `/decimal/float-demo` | float 精度比較デモ |
| GET | `/decimal/validate` | Decimal バリデーション |
| POST | `/decimal/compare` | 大小比較 |
| GET | `/decimal/precision` | 現在の計算精度 |

---

## テスト結果

**42 passed**

```
42 passed in 0.37s
```

---

## 摩擦ポイント

### F-1: `ROUND_HALF_EVEN`（銀行家丸め）の挙動が直感と異なる（深刻度: 低）

**事象**: `round_decimal("2.5", 0, "ROUND_HALF_EVEN")` → `"2"`（偶数方向）。
Python の組み込み `round(2.5)` も `2` を返すが（banker's rounding）、
多くの現場では「4捨5入」を期待して `ROUND_HALF_UP` を使う。

**原因**: `ROUND_HALF_EVEN` は統計的偏りを最小化するため偶数方向に丸める。
**対応**: ドキュメントに丸めモードの違いを表で説明し、金融計算ではデフォルトを `ROUND_HALF_UP` に設定した。

---

## 観察点

### 観察1: `float` vs `Decimal` の精度差

```python
0.1 + 0.2          # 0.30000000000000004
Decimal("0.1") + Decimal("0.2")  # 0.3

0.1 + 0.2 == 0.3   # False
Decimal("0.1") + Decimal("0.2") == Decimal("0.3")  # True
```

`Decimal` は文字列から初期化する必要がある。`Decimal(0.1)` は float の誤差を引き継ぐ。

### 観察2: `quantize()` による金融計算の標準パターン

```python
tax = (price * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

`quantize(Decimal("0.01"))` が「小数点以下2桁」を指定する慣用表現。
`Decimal(10) ** -2` と等価。`quantize` なしで演算すると桁数が増加する。

### 観察3: `Decimal("Infinity")` と `is_finite()` の組み合わせ

```python
def parse_decimal_safe(value: str) -> Decimal | None:
    result = Decimal(value)
    if not result.is_finite():  # Infinity / -Infinity / NaN を拒否
        return None
    return result
```

`Decimal("Infinity")`, `Decimal("NaN")`, `Decimal("sNaN")` は `InvalidOperation` を
投げずに正常に生成される。`is_finite()` チェックが必要な理由がここにある。

### 観察4: `split_bill` の ROUND_CEILING で全員が必ず払える金額に

```python
# 1000 / 3 = 333.333...
# ROUND_CEILING で 333.34 に切り上げ → 全員が333.34払うと 1000.02 になるが
# これは「端数は最初の人が多く払う」設計ではなく「全員同額で超えたら少し多い」設計
per_person = (total / num_people).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
```

---

## nene2-python フレームワークとの統合

- `BinaryOpBody`, `RoundBody`, `TaxBody` 等の Pydantic モデルで `max_length=30` を設定
- `_validate_decimal()` ヘルパーが `parse_decimal_safe()` を呼び出し、不正入力に一貫した 422 を返す
- セキュリティヘッダーとリクエストIDが全レスポンスに付与されている

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`Decimal` のコンストラクターに **文字列**を渡す必要がある点は最初のつまずき。

**ドキュメント理解**: `Decimal("0.1")` vs `Decimal(0.1)` の違いを説明する必要がある。  
**事故リスク**: 高。`Decimal(0.1)` で float 誤差を引き継ぐコードを書きがち。  
**規約の使いやすさ**: `parse_decimal_safe()` のファクトリ関数パターンは使いやすい。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存コードの `float` を `Decimal` に置換するとき `str()` 経由が必要なことを知らない。

**コピペ可能性**: `calculate_tax()` パターンはそのままコピーして使える。  
**拡張時の罠**: `quantize()` の `places` と `Decimal("0.01")` の関係が初見でわかりにくい。  
**セキュリティ的な事故リスク**: 中。負の価格・税率のバリデーション欠如（ペンテストで発見）。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS の `number` 型が浮動小数点演算なので、バックエンドが `Decimal` で正確に計算することの重要性を理解できる。

**エラーレスポンスの質**: 422 に `field_name` が含まれるため、フロント側のフォームバリデーションと対応しやすい。  
**Python 固有概念の学習コスト**: `quantize` は JS には直接対応物がないが、「N桁に揃える」と説明すればわかる。  
**事故リスク**: 低。HTTP 境界で `max_length` と `is_finite()` が守っている。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

金融システムで `Decimal` は必須。`quantize(ROUND_HALF_UP)` パターンを見れば即理解できる。

**他フレームワークとの差異**: Django の `DecimalField` はモデル側で `decimal_places` を指定するが、
このFTでは演算ごとに `quantize()` を呼ぶ明示的スタイル。どちらも正しい。  
**nene2-python の薄さへの評価**: ドメインロジック（金融計算）が HTTP 層から完全に独立している点が評価できる。  
**本番投入可能性**: ビジネスロジックバリデーション（範囲チェック）を追加すれば本番品質。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

ペンテストで発見されたビジネスロジック欠如（負の価格・100%超割引）は Issue 化が必要。

**コードレビューチェックポイント**:
- [x] `Infinity`, `NaN` が `is_finite()` でブロックされているか — OK
- [x] ゼロ除算が安全に処理されているか — `decimal_div()` で None 返却 ✅
- [ ] `calculate_tax()` の `tax_rate` に範囲制限がない — `0 <= tax_rate <= 2` 程度のバリデーションが必要
- [ ] `calculate_discount()` の `discount_percent` が 0〜100 のチェックがない
- [ ] Unicode 全角数字（`'１２３'`）が通過する — Decimal コンストラクターが Unicode digit を受け入れる

**チームでの安全な共有パターン**: `parse_decimal_safe()` を必ず経由するルールをチーム内で徹底することが必要。  
**ツール追加の必要性**: ruff には `Decimal(float)` を禁止するルールがないため、コードレビューで手動確認が必要。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md の「数値フィールドに `ge` / `le` / `gt` / `lt` 範囲制限があるか」ポリシーに対して、
`Decimal` 型は文字列で受け取るため Pydantic の数値制限が適用されない点が設計的な空白。

**ポリシー達成度**: 中（Pydantic で数値範囲制限できない文字列 Decimal の扱いが未定義）  
**「初心者でも安全な API」達成度**: 中（Infinity/NaN は守られているがビジネスルール違反は通過）  
**設計上の負債**: 文字列 Decimal の範囲バリデーションパターンをフレームワークに追加する必要がある  
**Follow-up Issue 候補**: `Pydantic Annotated` で `DecimalStr` 型エイリアスを定義して範囲制限を組み込む

---

## クラッカーペンテスト（FT176: 172 + 4 = 176）

> **実施方針**: 金融計算 API は「数値の正確さ」と「ビジネスロジックの整合性」の両面から攻撃できる。
> クラッカーは価格をマイナスにして不正な返金を引き出したり、税率を異常値にして計算を崩したりする。

### フェーズ1: 構造推測（攻撃者の視点）

- **OpenAPI から推測できる内部構造**:
  - 全フィールドが `str` 型 → `Decimal(str)` を内部で使っていると推測
  - `max_length=30` → 入力サイズ制限が文字数ベース（桁数ではない）
  - `num_people: int` に `ge=1, le=1000` → Pydantic 数値制限あり
  - `price`, `tax_rate` に数値範囲制限なし → バリデーション欠如の可能性

- **攻撃ベクターの仮説**:
  1. `Infinity`, `NaN` を渡してランタイムエラーを引き起こす
  2. 負の価格・100%超の税率でビジネスロジックを崩す
  3. Unicode 文字を数値として送り込む
  4. 科学表記（`1e100`）で予期しない巨大数を計算させる
  5. 精度の高い計算を大量に送ってCPUを枯渇させる

### フェーズ2: 攻撃実行ログ

#### A. Pydantic バイパス・型強制攻撃

```
a='Infinity': 422 Invalid decimal: a='Infinity'         ← ブロック ✅
a='-Infinity': 422                                       ← ブロック ✅
a='NaN': 422                                             ← ブロック ✅
a='sNaN': 422                                            ← ブロック ✅
a='inf': 422                                             ← ブロック ✅
a='-inf': 422                                            ← ブロック ✅
a='nan': 422                                             ← ブロック ✅

a='1e10': 200 result=10000000000                         ← 通過（有限値として正当）
a='1E308': 200 result=1.000...E+308                      ← 通過（有限値として正当）
a='1e100': 200 result=1.000...E+100                      ← 通過（有限値として正当）

a=123 (int type): 422 string_type error                  ← Pydantic が str を要求 ✅
```

**結果**: Infinity/NaN は全7種類ブロック。科学表記は有限値として通過（許容動作）。

#### B. ビジネスロジック攻撃

```
tax_rate=2.0 (200%超): 200 tax=2000.00, total=3000.00   ← 突破 ⚠️
price=-1000 (負の価格): 200 tax=-100.00, total=-1100.00 ← 突破 ⚠️
discount_percent=-10 (負割引): 200 → 値上がり           ← 突破 ⚠️
discount_percent=150 (100%超): 200 discounted=-500.00   ← 突破 ⚠️
div by zero: 422                                         ← ブロック ✅
```

**結果**: 数値範囲バリデーションが未実装のため、負の価格・異常税率が通過。
金融 API として使う場合はビジネスロジックレベルの制約が必要。

#### C. 境界値・エッジケース攻撃

```
a="" (空文字): 422 Invalid decimal                       ← ブロック ✅
len=30 (上限ちょうど): 200                               ← 通過（正常） ✅
len=31 (上限超え): 422 string_too_long                   ← Pydantic ブロック ✅
28桁 all-9s + 1: 200 result=1E+28                        ← 通過（正常） ✅
全角数字 '１２３' + 1: 200 result='124'                  ← 通過（予期しない動作）⚠️
```

**発見**: Python の `Decimal` コンストラクターは Unicode の全角数字（`'１２３'`）を受け付け、
`123` と同じ値として扱う。`parse_decimal_safe()` は `InvalidOperation` が発生しないため通過する。
金融 API でユーザーが全角数字を入力した場合、期待通りに動作するが、
入力形式の正規化なしに通過することに開発者が気づいていない可能性がある。

#### D. 情報収集攻撃

```
Invalid mode 'HACKED': 422 Unknown rounding mode: 'HACKED'  ← 安全なエラーメッセージ ✅
不正入力のエラー: 内部パス・スタックトレースなし ✅
```

**結果**: エラーメッセージは適切に制御されている。

#### E. DoS 試み

```
100回 div(1/3): 0.321s (3.2ms/req)                       ← 正常速度 ✅
50回 mul(28桁×28桁): 0.163s (3.3ms/req)                  ← 正常速度 ✅
攻撃後の精度: 28 (不変)                                   ← グローバル状態汚染なし ✅
```

**結果**: `1e100 + 1e100` のような巨大数演算も正常速度。
`decimal.getcontext().prec` はスレッドローカルなため、攻撃による変更は他スレッドに影響しない。

### フェーズ3: 攻撃まとめ

| 攻撃カテゴリ | 試みた攻撃数 | 突破 | 耐えた | 予期しない動作 |
|---|---|---|---|---|
| Pydantic バイパス（Inf/NaN） | 7 | 0 | 7 | 0 |
| 型強制（int型フィールド） | 1 | 0 | 1 | 0 |
| ビジネスロジック（範囲） | 4 | 4 | 0 | 0 |
| 境界値（長さ・文字種） | 5 | 0 | 4 | 1 |
| 情報収集（エラー解析） | 2 | 0 | 2 | 0 |
| DoS（大量・高精度計算） | 3 | 0 | 3 | 0 |

**攻撃耐性評価**: 軽微な問題あり（ビジネスロジックバリデーション欠如）

**発見した弱点**:
1. **MEDIUM**: `calculate_tax()`, `calculate_discount()` に価格・税率・割引率の範囲制限なし
   - 負の価格（`-1000`）→ 負の税額
   - 200%の税率（`2.0`）→ 元価格の3倍
   - 150%の割引（`150`）→ マイナス価格

2. **LOW**: Unicode 全角数字（`'１２３'`）が `Decimal` に通過する
   - `parse_decimal_safe` は `is_finite()` で判定するが、Unicode digit は有限値なので通過
   - 機能的には正しく動作するが、予期しない入力形式

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 高 | `calculate_tax()`, `calculate_discount()` に価格・税率・割引率の範囲バリデーションを追加 | fix |
| 中 | `parse_decimal_safe()` に ASCII 数字のみ許可するオプションを追加（Unicode digit の予期しない受け入れを防ぐ） | feat |
| 中 | 文字列 Decimal の `Annotated` 型エイリアス（`PositiveDecimalStr`, `TaxRateStr`）をフレームワークに追加 | feat |
| 低 | `Decimal(0.1)` を禁止するカスタム ruff ルールの検討 | chore |

---

## まとめ

FT176 では `decimal.Decimal` による精度の高い金融計算を実装した。
`float` との精度差（`0.1 + 0.2 != 0.3` 問題）、`quantize()` による丸め制御、
`is_finite()` による `Infinity`/`NaN` ブロックを確認した。

クラッカーペンテストでは Infinity/NaN の全種類が正常にブロックされたが、
ビジネスロジックレベルのバリデーション（負の価格・100%超の税率）が欠如していることを発見した。
金融 API では「計算として正しい値」と「ビジネスとして許容できる値」の区別が重要で、
`parse_decimal_safe()` の技術的バリデーションだけでは不十分であることが確認された。

次の FT177 は 177 % 3 = 0 → セキュリティ診断が必要。
