# FT174: itertools モジュール

**日付**: 2026-05-21
**テーマ**: `itertools` による無限イテレーター・組み合わせ・グルーピング・安全な消費
**セキュリティ診断**: **あり**（FT174: 174 % 3 = 0）

---

## 概要

Python 標準ライブラリの `itertools` モジュールを検証する。
無限イテレーター（`count`, `cycle`, `repeat`）、フィルター（`takewhile`, `dropwhile`, `compress`）、
グルーピング（`groupby`）、組み合わせ論的操作（`combinations`, `permutations`, `product`）、
累積（`accumulate`）を実装し、特に **組み合わせ爆発と無限ループによる DoS** への防御パターンを確認する。

このFTで確認する点:
- `islice` による無限イテレーターの安全な消費
- `groupby` の「ソート済み入力が必要」という仕様上の落とし穴
- `combinations` / `permutations` / `product` の組み合わせ爆発 DoS 防止
- `MAX_TAKE` / `MAX_COMBO_INPUT` / `MAX_COMBO_OUTPUT` による多層防御
- Pydantic `ge` / `le` による HTTP 境界でのサニタイズ

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft174-itertools/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `take(n, iterable)` | 汎用 islice ラッパー（上限 MAX_TAKE） |
| `count_range(start, step, limit)` | `itertools.count` から limit 件取り出す |
| `cycle_values(values, limit)` | `itertools.cycle` で繰り返す（limit 件） |
| `repeat_value(value, times)` | `itertools.repeat` 有限版 |
| `chain_lists(*lists)` | 複数リストをフラット結合 |
| `sliding_window(seq, size)` | スライディングウィンドウ（`pairwise` 活用） |
| `compress_by_mask(data, mask)` | マスクフィルター |
| `takewhile_positive(numbers)` | 正の数が続く間だけ取り出す |
| `dropwhile_negative(numbers)` | 負の数をスキップして以降を取り出す |
| `group_by_first_char(words)` | 先頭文字でグルーピング |
| `group_consecutive(numbers)` | 連続整数をグループ化 |
| `combinations_safe(items, r)` | DoS 防止付き組み合わせ |
| `permutations_safe(items, r)` | DoS 防止付き順列 |
| `product_safe(items, repeat)` | DoS 防止付きデカルト積（repeat 上限4） |
| `running_total(numbers)` | `accumulate` で累積和 |
| `running_max(numbers)` | `accumulate(max)` で累積最大値 |
| `pairwise_diffs(numbers)` | `pairwise` で差分リスト |
| `flatten_once(nested)` | `chain.from_iterable` で1段展開 |
| `batched_items(items, size)` | バッチ分割 |
| `roundrobin(*iterables)` | ラウンドロビン消費 |

DoS 防止定数:

| 定数 | 値 | 用途 |
|---|---|---|
| `MAX_TAKE` | 10,000 | 無限イテレーターからの最大取り出し件数 |
| `MAX_COMBO_INPUT` | 20 | 組み合わせ系関数への入力リスト上限サイズ |
| `MAX_COMBO_OUTPUT` | 5,000 | 組み合わせ系関数の出力件数上限（islice） |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/itertools/count` | count イテレーター（limit 付き） |
| GET | `/itertools/cycle` | cycle イテレーター（limit 付き） |
| GET | `/itertools/repeat` | repeat（times 付き） |
| POST | `/itertools/chain` | リスト結合 |
| POST | `/itertools/compress` | マスクフィルター |
| GET | `/itertools/takewhile` | 正の数フィルター |
| GET | `/itertools/dropwhile` | 負の数スキップ |
| POST | `/itertools/group-words` | 先頭文字グルーピング |
| POST | `/itertools/group-consecutive` | 連続整数グルーピング |
| POST | `/itertools/combinations` | 組み合わせ |
| POST | `/itertools/permutations` | 順列 |
| POST | `/itertools/product` | デカルト積 |
| POST | `/itertools/accumulate` | 累積和・累積最大値 |
| POST | `/itertools/pairwise-diffs` | 差分リスト |
| POST | `/itertools/flatten` | 1段展開 |
| POST | `/itertools/batch` | バッチ分割 |
| POST | `/itertools/roundrobin` | ラウンドロビン |
| GET | `/itertools/limits` | DoS 防止定数の公開 |

---

## テスト結果

**50 passed**

```
50 passed in 0.49s
```

---

## 摩擦ポイント

### F-1: `itertools.groupby` はソート済み入力が必要（深刻度: 中）

**事象**: `groupby(["banana", "apple", "cherry"], key=lambda w: w[0])` は3グループを返すが、
`groupby(["apple", "banana", "apple"], key=lambda w: w[0])` は `"apple"` が2グループになる。

**原因**: `groupby` は「連続する同じキー」でグループを作る。ソートしていないと断片化する。

**対応**: `group_by_first_char()` の実装で `sorted(words)` を前処理として追加。
ドキュメントに「ソート済み前提」を明記した。

---

## 観察点

### 観察1: `islice` による多層防御パターン

```python
MAX_TAKE = 10_000
MAX_COMBO_INPUT = 20
MAX_COMBO_OUTPUT = 5_000

def combinations_safe(items: list[str], r: int) -> list[tuple[str, ...]]:
    items = items[:MAX_COMBO_INPUT]   # レイヤー1: 入力サイズ制限
    r = max(1, min(r, len(items)))   # レイヤー2: r のクランプ
    return list(itertools.islice(    # レイヤー3: 出力件数制限
        itertools.combinations(items, r), MAX_COMBO_OUTPUT
    ))
```

HTTP 境界では Pydantic が `le=MAX_COMBO_INPUT` でも弾く（4層目）。
`P(20,10) = 670,442,572,800` という天文学的順列数が 5,000 件・7ms で完了するのは
`islice` がジェネレーターを遅延評価するから。全件生成せずに先頭だけ取る。

### 観察2: `itertools.pairwise` (Python 3.10+)

```python
def pairwise_diffs(numbers: list[int]) -> list[int]:
    return [b - a for a, b in itertools.pairwise(numbers)]
# [1, 4, 9, 16] → [3, 5, 7]
```

Python 3.10 で追加された `pairwise` は、スライディングウィンドウ size=2 の標準実装。
`zip(lst, lst[1:])` の冗長な書き方が不要になった。

### 観察3: `group_consecutive` の enumeration トリック

```python
def group_consecutive(numbers: list[int]) -> list[list[int]]:
    for _, group in itertools.groupby(enumerate(numbers), key=lambda t: t[1] - t[0]):
        result.append([v for _, v in group])
```

`enumerate([1, 2, 3, 7, 8])` → `[(0,1),(1,2),(2,3),(3,7),(4,8)]`
`value - index` = `[1, 1, 1, 4, 4]` → 同じ値が連続する = 連続した整数

### 観察4: `chain_lists(*lists)` の `*` アンパック

```python
def chain_lists(*lists: list[str]) -> list[str]:
    return list(itertools.chain(*lists))
```

`itertools.chain` は複数のイテラブルを引数に取る。
`itertools.chain.from_iterable(lists)` と等価だが、
`chain(*lists)` の方が意図が明確。`*lists` のアンパックがリストのリストを展開する。

---

## nene2-python フレームワークとの統合

- `nene2.middleware` の3ミドルウェアを LIFO 順序で追加、`test_security_headers` でヘッダー確認
- 全 POST エンドポイントで Pydantic モデルに `max_length` を設定（リスト要素数の上限）
- `get_cycle` の `values: list[str] = Query(max_length=50)` は Query パラメーターのリスト制限
- 定数（`MAX_TAKE`, `MAX_COMBO_INPUT`, `MAX_COMBO_OUTPUT`）を `/itertools/limits` で公開し、クライアントが安全な入力サイズを事前確認できるよう設計

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`itertools` はドキュメントが豊富で、各関数の用途は例が見れば理解できる。
ただし「なぜ `groupby` にソートが必要なのか」は一度ハマらないと気づけない。

**ドキュメント理解**: `islice` の「n件で切り取る」という役割は直感的。
`accumulate` の `func` 引数（第2引数に `max` を渡せること）はドキュメントを読まないと気づかない。  
**事故リスク**: 高。`itertools.cycle` を `islice` なしで呼ぶと無限ループになる。
このFTでは `MAX_TAKE` による安全なラッパーを提供しているが、
直接 `cycle` を使う初心者は必ずハマる。  
**規約の使いやすさ**: `combinations_safe()` のような命名で「Safe=islice 制限付き」を
明示するパターンはわかりやすい。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`itertools` を「なんとなく chain だけ使う」スタイルの人には、
このFTの `MAX_COMBO_INPUT` / `MAX_COMBO_OUTPUT` の設計は学習材料になる。

**コピペ可能性**: `combinations_safe()` の3層防御パターン（入力制限・r クランプ・islice）は
コピペで正しく動く。  
**拡張時の罠**: 「もっとたくさん返してほしい」と言われて `MAX_COMBO_OUTPUT` を増やすと
大きな `r` で応答時間が急増する（二項係数は急速に増大）。  
**セキュリティ的な事故リスク**: 中。直接 `combinations(range(1000), 100)` を書けば
サーバーがハングする。安全なラッパーなしの実装は危険。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`/itertools/limits` エンドポイントで制限値を公開する設計は API クライアント視点で親切。
「送れる最大サイズ」を事前に取得して UI 側でバリデーションできる。

**エラーレスポンスの質**: 422 時に Pydantic が `loc`, `msg`, `type` を返すため
クライアントはどのフィールドが問題かを識別できる。  
**Python 固有概念の学習コスト**: ジェネレーター・遅延評価の概念は Node.js の
Generator とほぼ対応するため理解しやすい。`islice` はほぼ `Array.from({length: n}, ...)` と同等。  
**事故リスク**: 低。HTTP 境界の制限が Pydantic + 定数で二重に守られている。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`itertools` の組み合わせ爆発 DoS は過去に本番事故を見たことがある人なら即座に理解できる。
多層防御（Pydantic + クランプ + islice）の設計は好意的に評価されるはず。

**他フレームワークとの差異**: Django の `Paginator` は内部で全件 count するが、
`islice` は遅延評価なので計算量が O(output_count) で済む点が優れている。  
**nene2-python の薄さへの評価**: `MAX_TAKE`, `MAX_COMBO_INPUT` を定数として明示し、
`/limits` で公開する設計は「薄い HTTP 層でドメインロジックを分離」の良い例。  
**本番投入可能性**: チームで `combinations` を使う際は必ず `combinations_safe()` 経由を
コーディング規約に追加することを推奨する。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

組み合わせ爆発 DoS の多層防御は適切。ただし `roundrobin()` の実装に気になる点がある。

**コードレビューチェックポイント**:
- [x] `itertools.cycle()` が必ず `islice` でラップされているか — `cycle_values()` で確認
- [x] `combinations`, `permutations`, `product` に入力・出力の両方に上限があるか — OK
- [ ] `roundrobin()` が `while nexts` ループで動作しているが、全イテレーターが空のとき正しく終了するか — `StopIteration` 処理が正しい
- [ ] 文字列要素の max_length が `list[str]` の要素レベルで制限されていない — `max_length=1000` はリスト長の制限であり、各文字列の長さは無制限

**チームでの安全な共有パターン**: `_safe` サフィックスの命名規約でラッパー関数を明示するパターンはチーム内で徹底しやすい。  
**ツール追加の必要性**: `itertools` の無限イテレーター直接使用を ruff で禁止する設定は標準では存在しないため、チーム規約として文書化が必要。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md の「文字列フィールドには長さ制限」ポリシーについて、
`list[str]` の**要素文字列**のサイズ制限が未実装。リスト長は `max_length` で制限しているが、
各要素が 1MB の文字列でも通過してしまう。

**ポリシー達成度**: 中（リスト要素の文字列長が未制限）  
**「初心者でも安全な API」達成度**: 高（`combinations_safe` / `cycle_values` のラッパーが防衛線）  
**設計上の負債・ドキュメント不足**: `list[str]` 要素の `max_length` 制限方法が
Pydantic v2 では `Annotated[list[Annotated[str, Field(max_length=200)]], Field(max_length=1000)]`
という冗長な構文になるため、プロジェクト共通の型エイリアス定義が必要  
**Follow-up Issue 候補**: `list[str]` 要素レベルの文字列長制限パターンをフレームワークに追加

---

## セキュリティ診断（FT174: 174 % 3 = 0）

> **診断方針**: 組み合わせ爆発・無限ループ・型強制による DoS を主要な攻撃ベクターとして検証する。
> itertools は純粋計算のみでファイル・DB・外部通信を行わないため、
> SQLi / SSRF / パストラバーサルは対象外。

### 1. OWASP API Security Top 10 (2023)

#### API1: オブジェクトレベルの認可不備 (BOLA / IDOR)
- ✅ 対象外: このFTはステートレス計算のみ。ユーザー固有リソースなし

#### API2: 認証の破損 (Broken Authentication)
- ✅ 対象外: 認証不要のサンドボックス

#### API3: オブジェクトプロパティレベルの認可不備 (Mass Assignment)
- [x] extra フィールド（`"extra": "injected"`）を POST しても無視される
- **結果**: ✅ Pydantic がデフォルトで追加フィールドを無視。内部モデルに漏洩なし
- **注記**: `model_config = ConfigDict(extra="forbid")` を追加すれば 422 で明示的に拒否可能

#### API4: 無制限リソース消費 (Unrestricted Resource Consumption)
実際に攻撃的な値を試験した:
```
GET /itertools/count?limit=99999  → 422 (le=MAX_TAKE=10000)
POST /product {"items": ["a","b"], "repeat": 100} → 422 (le=4)
POST /combinations {"items": 20個, "r": 10} C(20,10)=184756
  → count: 5000 (islice 上限), elapsed: 7ms
POST /permutations {"items": 20個, "r": 10} P(20,10)=670,442,572,800
  → count: 5000 (islice 上限), elapsed: 7ms ← 遅延評価が機能
```
- **結果**: ✅ 3層防御（Pydantic `le` → 入力クランプ → `islice`）が有効。670兆通りの順列も7msで返す

#### API5: 機能レベルの認可不備 (Broken Function Level Authorization)
- ✅ 対象外: 管理者エンドポイントなし

#### API6: SSRF
- ✅ 対象外: URL を受け取るエンドポイントなし

#### API7: セキュリティの設定ミス
- [x] `SecurityHeadersMiddleware` が全レスポンスに `x-content-type-options: nosniff`, `x-frame-options: DENY` を付与
- [x] `RequestIdMiddleware` が `x-request-id` を付与
- [x] 422 エラー時にスタックトレース非公開を確認
- **結果**: ✅ 全通過

#### API8〜API10
- ✅ 対象外または適用なし

---

### 2. インジェクション攻撃

#### SQL インジェクション
- ✅ 対象外: DB 操作なし

#### コマンドインジェクション
- ✅ 対象外: `subprocess`, `os.system` 使用なし。`itertools` は純粋 Python

#### パストラバーサル
- ✅ 対象外: ファイル操作なし

#### SSTI
- ✅ 対象外: テンプレートエンジン使用なし

---

### 3. 認証・認可
- ✅ 対象外: 認証不要のサンドボックス

---

### 4. 入力バリデーション

テスト結果:
```python
# Pydantic 型強制テスト
r="2" (string → int):  200, count=3  → 文字列がintに変換される（Pydantic v2 laxモード）
r=1.9 (float → int):   422           → 小数点以下がある float は拒否 ✅
r=-1 (negative int):   422           → ge=1 で拒否 ✅
batch_size=0:           422           → ge=1 で拒否 ✅
limit=99999:            422           → le=10000 で拒否 ✅
```
- **発見**: `r="2"` (文字列 "2") は Pydantic v2 lax モードで `int` に変換されて通過する。
  これは許容動作（JSON で数値を文字列として送る慣習があるため）だが、
  `ConfigDict(strict=True)` を使えば明示的に拒否できる。
- **ヌルバイト**: `"\x00evil"` は計算処理のみなので通過。DB 書き込みや OS 処理がないため無害。

---

### 5. 情報漏洩

- [x] `limit=notanint` → 422、Pydantic エラー詳細のみ返却、スタックトレースなし
- [x] セキュリティヘッダーに `Server:` ヘッダーなし
- **結果**: ✅ 安全

---

### 6. Python / FastAPI 固有の攻撃ベクター

#### 組み合わせ爆発 DoS（itertools 固有）
itertools は数学的に爆発するリソース消費の源泉になりえる:
```python
# 保護なし実装での理論的影響:
list(itertools.combinations(range(1000), 100))  # 天文学的 → メモリ枯渇
list(itertools.permutations(range(20)))          # 20! = 2.43京 → メモリ・CPU 枯渇
list(itertools.cycle([1]))                       # 無限ループ → プロセス停止
```

**保護結果**:
- `islice` による遅延評価で天文学的組み合わせを O(output_count) で処理 ✅
- Pydantic `le` + クランプ + `islice` の3層防御 ✅
- HTTP 境界でのリスト長制限（`max_length=20`） ✅

#### ReDoS
- ✅ 対象外: 正規表現使用なし

#### pickle / yaml / marshal インジェクション
- ✅ 対象外: シリアライゼーション処理なし

#### 非同期レースコンディション
- ✅ 対象外: 非同期処理・グローバル状態共有なし

#### 型強制攻撃（Pydantic Type Coercion）
- `r="2"` → `int(2)`: lax モードで変換 ⚠️ 許容動作だが `strict=True` で厳格化可能
- `r=1.9` → `422`: 小数点付き float は int フィールドで拒否 ✅
- **結論**: 許容できる型強制のみ。数値的に有効な範囲なので悪用不可

---

### 7. 依存関係の脆弱性スキャン

```
uv run pip-audit
Found 1 known vulnerability in 1 package
Name  Version ID             Fix Versions
pyjwt 2.12.1  PYSEC-2025-183 (なし)
```

- **PYSEC-2025-183**: PyJWT の既知 CVE。`mcp>=1.0` の推移的依存（FT165 で調査済み）。
  直接依存として追加していないため修正不可。mcp のアップデートを待つ。
- **スキャン結果**: CRITICAL: 0件 / HIGH: 0件 / MEDIUM: 0件 / LOW: 1件（対応待ち）
- **対応方針**: 許容（mcp の更新を待つ。このFTは JWT を直接使用しない）

---

### 診断サマリー

| カテゴリ | 結果 | 最重要発見 |
|---|---|---|
| OWASP API Security Top 10 | ✅ 全通過 | API4: 3層防御が有効（C/P 爆発も7msで処理） |
| SQL インジェクション | ✅ 対象外 | - |
| コマンドインジェクション | ✅ 対象外 | - |
| パストラバーサル | ✅ 対象外 | - |
| SSTI | ✅ 対象外 | - |
| 認証・認可 | ✅ 対象外 | - |
| 入力バリデーション | ⚠️ 軽微 | `r="2"` が lax モードで通過（無害） |
| 情報漏洩 | ✅ 全通過 | スタックトレース非公開 |
| 組み合わせ爆発 DoS | ✅ 全防御 | P(20,10)=670兆通りも5000件・7ms |
| 型強制攻撃 | ⚠️ 軽微 | float→int(整数部のみ)は許容。`le`で範囲制限済み |
| 依存関係 CVE | ⚠️ 対応待ち | PYSEC-2025-183 (PyJWT, mcp の推移的依存) |

**総合評価**: 合格（組み合わせ爆発 DoS 防御が適切に実装されている）  
**発見した脆弱性**: 0件（CRITICAL/HIGH/MEDIUM なし）  
**軽微な指摘**: 2件（型強制・要素文字列長未制限）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | `list[str]` 要素レベルの文字列長制限パターンをフレームワークに追加（`Annotated` 型エイリアス） | feat |
| 低 | `groupby` の「ソート済み前提」をドキュメント / 型システムで強制する方法を検討 | docs |
| 低 | PYSEC-2025-183 (PyJWT): mcp の更新を監視する | security |

---

## まとめ

FT174 では `itertools` の主要関数を実装し、組み合わせ爆発 DoS への多層防御パターン（Pydantic `le` → 入力クランプ → `islice` 遅延評価）が有効であることを実証した。
P(20,10) = 670兆通りの順列を7ms・5000件で安全に返せることを確認。
`itertools.cycle` / `count` / `repeat` の無限イテレーターは `islice` ラッパーなしでは
即座に DoS になるため、チーム規約として `_safe` サフィックスパターンの徹底が重要。

次の FT175 は 175 % 3 = 1 → セキュリティ診断なし。175 % 4 ≠ 0 → ペンテストなし。
