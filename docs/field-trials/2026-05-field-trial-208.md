# FT208: itertools モジュール — chain / islice / groupby / product / combinations

**日付**: 2026-05-22
**テーマ**: Python `itertools` モジュールの chain / islice / groupby / product / combinations の実装と検証
**セキュリティ診断**: なし（208 % 3 = 1）
**クラッカーペンテスト**: あり（208 % 4 = 0）

---

## 概要

`itertools` モジュールは Python 標準ライブラリのイテレータ生成ツールキット。
今 FT では以下の関数を HTTP API として実装し、特にリソース消費攻撃（組み合わせ爆発）への
防御パターンを検証した。

| 関数 | ユースケース |
|---|---|
| `chain` | 複数リストの連結 |
| `islice` | ページング処理 |
| `groupby` | キー別グループ化 |
| `product` | デカルト積（サイズ・カラー組み合わせ等） |
| `combinations` / `combinations_with_replacement` | 組み合わせ生成 |
| `takewhile` / `dropwhile` | 閾値による分割フィルタリング |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft208-itertools/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `chain_iterables(sources)` | `chain(*sources)` で複数リストを結合 |
| `paginate(items, page, page_size)` | `islice` でページング処理 |
| `group_sorted_items(items, key_length)` | ソート後 `groupby` でグループ化 |
| `cartesian_product(sets)` | `product(*sets)` でデカルト積 |
| `generate_combinations(items, r, with_replacement)` | 組み合わせ生成（結果数上限チェック付き） |
| `split_by_threshold(numbers, threshold)` | `takewhile` / `dropwhile` で分割 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/itertools/chain` | 複数リスト結合 |
| POST | `/itertools/paginate` | ページング処理 |
| GET | `/itertools/paginate` | ページング（デモ用固定リスト） |
| POST | `/itertools/groupby` | キー別グループ化 |
| POST | `/itertools/product` | デカルト積 |
| POST | `/itertools/combinations` | 組み合わせ生成 |
| POST | `/itertools/split-threshold` | 閾値分割 |

---

## テスト結果

**26 passed**

```
26 passed in 0.60s
```

---

## 摩擦ポイント

### F-1: `combinations_with_replacement` の結果数が想定外に大きい

`MAX_COMBO_N=20`（アイテム数上限）・`MAX_COMBO_R=10`（r 上限）を設定していたが、
`combinations_with_replacement(n=20, r=10)` の結果数は C(29, 10) = **20,030,010 件**。

クラッカーペンテスト中に発見。`math.comb` で事前計算して上限チェックする防御を追加した。

```python
# 修正前: n・r の上限のみチェック → 2000万件が生成される
combos = [list(c) for c in itertools.combinations_with_replacement(items, r)]

# 修正後: 結果数を事前計算して上限チェック
expected = math.comb(n + r - 1, r)  # combinations_with_replacement の結果数
if expected > MAX_COMBO_RESULTS:    # MAX_COMBO_RESULTS = 1000
    return None  # ハンドラーが ValidationException に変換
```

---

## 観察点

### 観察1: `groupby` はソート済み入力を前提とする

```python
from itertools import groupby

# ❌ ソートなしでは同じキーでも別グループになる
data = ["Apple", "Banana", "Avocado"]
for key, group in groupby(data, key=lambda x: x[0]):
    print(key, list(group))
# A ['Apple']
# B ['Banana']
# A ['Avocado']  ← 'A' が再び出現する

# ✅ ソート後に groupby を使う
data_sorted = sorted(data, key=lambda x: x[0])
for key, group in groupby(data_sorted, key=lambda x: x[0]):
    print(key, list(group))
# A ['Apple', 'Avocado']
# B ['Banana']
```

**`groupby` は連続する同じキーをグループ化する** — ソートなしでは意図しない分割が起きる。
SQL の GROUP BY と異なるため、Python 経験者でも見落としやすい。

### 観察2: `islice` は範囲外でも安全

```python
from itertools import islice

items = ["a", "b"]
list(islice(items, 10, 20))  # → [] （IndexError にならない）
list(islice(items, 0, 100))  # → ["a", "b"] （全件）
```

ページング実装で `page=9999` のような大きな値が来ても `islice` は安全に空リストを返す。
`items[start:end]` のスライスと同じ安全性を持ちながら、イテレータをメモリに展開しない。

### 観察3: `product` のデカルト積は急激に増える

```python
from itertools import product

# サイズ × カラー × 素材 = 3 × 3 × 4 = 36
list(product(["S", "M", "L"], ["red", "blue", "green"], ["cotton", "silk", "wool", "nylon"]))

# 10 セット × 各 10 要素 = 10^10 → メモリ不足
```

`product` は組み合わせ爆発の典型例。
nene2 フレームワークでは「結果数の事前チェック」を `ValidationException` で防御するパターンが重要。

### 観察4: `combinations_with_replacement` の結果数は `combinations` より多い

```python
# C(n, r) = n! / (r! * (n-r)!)
# C(3, 2) = 3 (["ab", "ac", "bc"])

# C(n+r-1, r) for with_replacement
# C(3+2-1, 2) = C(4, 2) = 6 (["aa", "ab", "ac", "bb", "bc", "cc"])
```

n と r が同じ場合、`combinations_with_replacement` の方が常に結果数が多い。
n=20, r=10 では:
- `combinations`: C(20, 10) = 184,756
- `combinations_with_replacement`: C(29, 10) = 20,030,010（108 倍）

アイテム数・r の上限だけでなく **結果数の上限** を `math.comb` で事前チェックすることが必須。

### 観察5: `takewhile` は最初の失敗で停止する（残りは見ない）

```python
from itertools import takewhile, dropwhile

# [1, 5, 2, 3] で threshold=4 の場合
list(takewhile(lambda x: x < 4, [1, 5, 2, 3]))  # → [1] （5 で停止、2,3 は確認しない）
list(dropwhile(lambda x: x < 4, [1, 5, 2, 3]))  # → [5, 2, 3]
```

`takewhile` は **最初に条件を満たさなくなった時点で停止** し、残りの要素は確認しない。
`filter()` とは異なり、「先頭から連続して条件を満たす部分」のみを取り出す。
ソート済みデータの範囲抽出に有用。

---

## クラッカーペンテスト

### ペンテスト結果: **堅牢**（全 12 攻撃をブロック）

| # | 攻撃ベクター | 結果 | ステータス |
|---|---|---|---|
| 1 | chain sources 21 個（上限超え） | ブロック | 422 |
| 2 | chain 合計 502 アイテム | ブロック | 422 |
| 3 | paginate page_size=101 | ブロック | 422 |
| 4 | product 爆発（10^4） | ブロック | 422 |
| 5 | combinations r > n（重複なし） | ブロック | 422 |
| 6 | combinations_with_replacement n=20 r=10（2000万件） | **修正後ブロック** | 422 |
| 7 | groupby 空白のみ | ブロック | 422 |
| 8 | threshold 最大整数値 (10^9) | 通過 | 200 |
| 9 | threshold 最小整数値 (-10^9) | 通過 | 200 |
| 10 | threshold オーバーフロー (10^10) | ブロック | 422 |
| 11 | product に SQL インジェクション形式文字列 | 安全（文字列として処理） | 200 |
| 12 | paginate page=9999（要素 2 件） | 安全（空リスト返却） | 200 |

**修正 F-1**: クラッカーペンテスト中に攻撃ベクター 6 を発見。
`math.comb` による事前チェックを追加し、再テストで 422 となることを確認。

---

## nene2-python フレームワークとの統合

- `itertools.product` / `combinations` など結果数が爆発しうる関数は
  **必ず `math.comb` で結果数を事前計算して上限チェック** を実施する。
- `groupby` は必ずソート後に使用する（`sorted(items, key=...)` → `groupby(sorted, key=...)`）。
- `islice` によるページングは `(page-1)*size` から `page*size+1` まで取得し、
  `has_more` フラグを `len(sliced) > page_size` で判定する。
- `takewhile` / `dropwhile` の動作（最初の失敗で停止）を API ドキュメントに明示する。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

大量データのページング機能を実装しようとしている。

**ドキュメント理解**: `islice(items, start, stop)` は `items[start:stop]` と同じ使い方ができる。
Python の標準 API と一致するため学習コストが低い。  
**事故リスク**: 中。`groupby` が「連続グループ化」であることは初心者が見落としやすい。
`sorted()` を忘れると意図しないグループになる（SQL の GROUP BY との混同）。  
**規約の使いやすさ**: `paginate()` のようなヘルパーにラップすれば初心者でも安全に使える。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

ECサイトの「全カラー × 全サイズ組み合わせ」エンドポイントを実装しようとしている。

**コピペ可能性**: `list(product(*sets))` は 1 行で書けて便利。コピペしやすい。  
**拡張時の罠**: `product` や `combinations_with_replacement` の結果数爆発は予測しにくい。
「10セット × 各5要素なら大丈夫」という感覚で書くと 5^10 = 976 万件になる。  
**セキュリティ的な事故リスク**: **高**。`math.comb` での事前チェックなしで本番実装すると DoS の原因になる。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

フロントエンドで実装していたページング処理をバックエンドに移行しようとしている。

**エラーレスポンスの質**: `has_more` フラグは React のページングコンポーネントに直接使える設計。  
**Python 固有概念の学習コスト**: JS の `Array.prototype.slice()` に相当する `islice` は直感的。
`itertools.product` は TS にない（`lodash` の `_.zip` でも代替できない）。  
**事故リスク**: 低。フロントエンドエンジニアは大量データ生成の経験が少ないが、
Pydantic の `max_length` と `math.comb` チェックで守られている。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

商品バリエーション（サイズ × カラー × 素材）の組み合わせ API を設計しようとしている。

**他フレームワークとの差異**: Django ORM の `values_list` + `distinct` と異なり、
Python レイヤーで組み合わせを生成するため DB に依存しない。
テストが DB なしで完結する点は有用。  
**nene2-python の薄さへの評価**: `math.comb` による事前チェックパターンを共通ヘルパーとして
`nene2.http.itertools_utils` に追加する価値がある。  
**本番投入可能性**: 結果数チェック付きの `generate_combinations` はそのまま本番使用可能。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

コードレビューで `itertools` の使用箇所を確認しようとしている。

**コードレビューチェックポイント**:
- [ ] `groupby` の前に `sorted()` が呼ばれているか
- [ ] `product` / `combinations` の結果数を事前計算して上限チェックしているか
- [ ] `islice` の引数が `(iterable, start, stop)` の順になっているか（`(iterable, stop)` と混同しやすい）
- [ ] `takewhile` / `dropwhile` の「最初の失敗で停止」動作が意図通りか
- [ ] `chain` の合計アイテム数に上限を設けているか

**チームでの安全なパターン**:
- `product` / `combinations` は `math.comb` で結果数チェック必須をコーディング規約に追加する
- `groupby` は `sorted()` とセットでラッパー関数化して使う

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高。全エンドポイントで `max_length` / 結果数上限チェック / `response_model` 明示を徹底。  
**「初心者でも安全な API」達成度**: 中。`groupby` の「ソート必須」制約と `combinations` の爆発リスクは
追加ドキュメントが必要。  
**設計上の負債**: `math.comb` による結果数事前チェックパターンを nene2 コアに追加する価値がある（低優先度）。  
**Follow-up Issue 候補**: なし（今 FT 内で修正完了）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 低 | `math.comb` による組み合わせ数事前チェックヘルパーを nene2 コアに追加検討 | enhancement |

---

## まとめ

`itertools` は一見シンプルだが、**組み合わせ爆発**という特有のリスクがある。
クラッカーペンテストで `combinations_with_replacement(n=20, r=10)` が 2000 万件生成される
ことを発見し、`math.comb` による事前チェックで防御した。

最大の学習ポイントは:
1. **`groupby` はソート後に使う** — 未ソートでは同キーが分散する（SQL の GROUP BY と別物）
2. **`combinations_with_replacement` の結果数は急増する** — `math.comb(n+r-1, r)` で事前チェック必須
3. **`islice` は範囲外でも安全** — `items[10000:]` が `[]` を返すのと同じ
4. **`takewhile` は最初の失敗で停止** — `filter()` ではなく「先頭連続部分の抽出」

次の FT209 は `209 % 3 = 2` → セキュリティ診断なし、`209 % 4 = 1` → クラッカーペンテストなし。
