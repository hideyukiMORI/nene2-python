# FT207: collections モジュール — namedtuple / defaultdict / Counter / deque

**日付**: 2026-05-22
**テーマ**: Python `collections` モジュールの namedtuple / defaultdict / Counter / deque の実装と検証
**セキュリティ診断**: あり（207 % 3 = 0）
**クラッカーペンテスト**: なし（207 % 4 = 3）

---

## 概要

`collections` モジュールは Python 標準ライブラリの中で最も頻繁に使われるユーティリティの一つ。
`namedtuple` で軽量 Value Object を定義し、`defaultdict` で集計処理、
`Counter` で頻度分析、`deque` で双方向キューを実装した。
今 FT ではそれぞれの型が API 境界でどのように扱われるかを検証した。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft207-collections/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `analyze_point(x, y)` | `namedtuple Point` で座標解析（距離・象限） |
| `analyze_rgb(r, g, b)` | `namedtuple RGB` で HEX コード・明度計算 |
| `count_words(text)` | `defaultdict[int]` で単語頻度を集計 |
| `group_by_first_letter(words)` | `defaultdict[list]` で先頭文字グループ化 |
| `analyze_text_chars(text, top_n)` | `Counter` で文字頻度を集計 |
| `diff_counters(first, second)` | `Counter` の集合演算で 2 リストを比較 |
| `manage_deque(...)` | `deque` への appendleft/append/popleft/pop 操作 |
| `build_recent_log(logs, capacity)` | 固定容量 `deque` で直近ログを保持 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/collections/point` | 座標解析（namedtuple Point） |
| POST | `/collections/rgb` | RGB 色解析（namedtuple RGB） |
| GET | `/collections/word-frequency` | 単語頻度集計（defaultdict） |
| POST | `/collections/group-by-letter` | 先頭文字グループ化（defaultdict） |
| GET | `/collections/char-frequency` | 文字頻度集計（Counter） |
| POST | `/collections/counter-diff` | Counter 差分比較 |
| POST | `/collections/deque-ops` | deque 操作 |
| POST | `/collections/recent-log` | 固定容量ログバッファ（deque） |

---

## テスト結果

**29 passed**

```
29 passed in 0.60s
```

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

`collections` の各クラスはシンプルで API 境界での扱いも明確だった。
唯一の注意点は mypy の `namedtuple` 型推論だが、Python 3.14 では `# type: ignore[misc]` が不要になっていた（開発環境は 3.14.5）。

---

## 観察点

### 観察1: `namedtuple` は軽量 Value Object だが型安全ではない

```python
Point = namedtuple("Point", ["x", "y"])
p = Point(3, 4)
p.x  # → 3（アクセスは便利）

# しかし型は Any として扱われる
p2 = Point("not_a_number", None)  # 実行時エラーにならない
```

API 境界で型安全が必要な場合は `dataclass(frozen=True, slots=True)` を使うべき。
`namedtuple` は読み取り専用の軽量タプルラッパーとして内部実装に留める。

### 観察2: `defaultdict` は「キーが存在しない」ケースを自動処理する

```python
from collections import defaultdict

freq: defaultdict[str, int] = defaultdict(int)
freq["new_key"] += 1  # KeyError にならない。0 + 1 = 1
freq["new_key"]       # → 1

groups: defaultdict[str, list[str]] = defaultdict(list)
groups["A"].append("Apple")  # KeyError にならない
```

手動 `if key not in d: d[key] = []` パターンが不要になる。
ただし `defaultdict` 自体は `dict` のサブクラスなので、
Pydantic モデルの戻り値型として使う場合は `dict(...)` に変換してから返す。

### 観察3: `Counter` の集合演算は直感的

```python
from collections import Counter

a = Counter(["x", "x", "y"])  # → Counter({'x': 2, 'y': 1})
b = Counter(["x", "z"])       # → Counter({'x': 1, 'z': 1})

b - a   # 追加分: Counter({'z': 1}) — b にあって a にないもの
a - b   # 削除分: Counter({'x': 1, 'y': 1}) — a にあって b にないもの
a & b   # 共通最小: Counter({'x': 1})
a | b   # 合算最大: Counter({'x': 2, 'y': 1, 'z': 1})
```

差分比較（追加・削除・共通・合算）を 4 行で書けるのは Counter の最大の強み。
`added = b - a` / `removed = a - b` のパターンは変更検出・ログ差分分析に有用。

### 観察4: `deque` の `maxlen` はリングバッファとして動作する

```python
from collections import deque

log: deque[str] = deque(maxlen=3)
log.append("a")  # ['a']
log.append("b")  # ['a', 'b']
log.append("c")  # ['a', 'b', 'c']
log.append("d")  # ['b', 'c', 'd'] ← 'a' が自動削除される
```

`maxlen` を設定した `deque` は固定容量のリングバッファとして動作する。
`collections.deque(logs, maxlen=capacity)` で全ログを一括ロードすると、
容量超過分は自動的に古い方から削除される。
スライディングウィンドウ / 最新 N 件保持のユースケースに最適。

### 観察5: `deque` の pop 超過は安全に処理できる

```python
dq: deque[str] = deque(["a"])
for _ in range(10):
    if dq:
        dq.popleft()  # 空になったら if で守る
```

`dq.popleft()` は空の deque に対して `IndexError` を送出する。
API では `if dq:` で pop 前にチェックすることで安全に処理できる。
空 deque への pop 超過リクエスト（`pop_left=10` で要素 1 個）は `items=[]` を返す。

---

## セキュリティ診断

### 診断結果: **合格**

#### 1. OWASP API Security Top 10 (2023)

| カテゴリ | 結果 | 備考 |
|---|---|---|
| API1: BOLA | 合格 | 個別リソースへのアクセス制御なし（コレクション操作のみ） |
| API4: リソース消費 | 合格 | `max_length` で全入力に上限設定済み |
| API7: SSRF | 合格 | 外部ネットワークアクセスなし |

#### 2. インジェクション攻撃

| 攻撃ベクター | 結果 | 備考 |
|---|---|---|
| SQL インジェクション | 合格 | DB アクセスなし |
| コマンドインジェクション | 合格 | `subprocess` / `os.system` 不使用 |
| パストラバーサル | 合格 | ファイルアクセスなし |
| SSTI | 合格 | テンプレートエンジン不使用 |

#### 3. 入力バリデーション

| テスト | 結果 | ステータスコード |
|---|---|---|
| `x=2e9`（数値上限超過） | 合格 | 422 |
| テキスト 5000 文字 | 合格 | 422 |
| リスト 1001 件 | 合格 | 422 |
| `maxlen=10001` | 合格 | 422 |
| ヌルバイト (`\x00`) | 合格 | 200（文字として処理、問題なし） |
| RTL オーバーライド (`‮`) | 合格 | 200（文字として処理、問題なし） |
| `pop_left=10` で要素 1 個 | 合格 | 200（空リストを安全に返す） |

#### 4. Python/FastAPI 固有

| 項目 | 結果 | 備考 |
|---|---|---|
| pickle 非使用 | 合格 | `collections` 自体は pickle 非使用 |
| `defaultdict` の無限ネスト | 合格 | API 境界で `dict` に変換済み |
| `Counter` 負値 | 合格 | `a - b` で 0 以下は自動除去される |
| namedtuple の型安全 | 合格 | API 境界は Pydantic BaseModel が守る |

#### 診断サマリー

`collections` モジュール自体はデータ構造ライブラリであり、外部リソースアクセスがない。
インジェクション攻撃の対象は DB・コマンド・ファイルアクセスで発生するため、
collections 単独の実装ではリスクが極めて低い。
リソース消費攻撃（大量データ投入）は Pydantic の `max_length` で防御済み。

---

## nene2-python フレームワークとの統合

- `namedtuple` は内部処理に使用し、レスポンスは `dataclass(frozen=True, slots=True)` で定義する。
  API 境界では型安全な Pydantic / dataclass を優先する。
- `defaultdict` の戻り値は `dict(...)` に変換してから返す。
  Pydantic が `defaultdict` を `dict` として正しくシリアライズするため問題ないが、
  意図を明確にするため変換する。
- リスト入力には `Field(max_length=MAX_ITEMS)` を必ず設定する（リソース消費防御）。
- `deque` の `pop` 操作は空チェックを必ず実施する（`IndexError` 防御）。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

単語の出現回数を集計するコードを書こうとしている。

**ドキュメント理解**: `defaultdict(int)` の `int` が「初期値ファクトリ」であることは最初は直感的でない。
`defaultdict(lambda: 0)` と等価と理解すれば使いやすくなる。  
**事故リスク**: 低。`defaultdict` は型安全でないが、API 境界は Pydantic が守る。
`defaultdict` を直接レスポンスとして返すと型エラーになるため、変換忘れでエラーに気づける。  
**規約の使いやすさ**: `dict(defaultdict_value)` の変換パターンを規約として明示すれば十分。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`Counter` を使って 2 つのリストの差分を計算しようとしている。

**コピペ可能性**: `added = b - a` / `removed = a - b` の 2 行は非常にコピペしやすい。  
**拡張時の罠**: `Counter` の減算は **0 以下の要素を除去する**。
`Counter({"x": 1}) - Counter({"x": 2})` は `Counter()` になる（`-1` にならない）。
`subtract()` メソッドを使えば負値が残る（差分の方向性で使い分けが必要）。  
**セキュリティ的な事故リスク**: 低。collections はデータ構造なのでインジェクションリスクなし。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JavaScript の `Map` / `Set` から Python の `collections` に移行しようとしている。

**エラーレスポンスの質**: 422 + `max_length` バリデーションエラーは明確。  
**Python 固有概念の学習コスト**: `Counter` の集合演算（`&` / `|`）は TS/JS にない。
`Set` の intersection/union に近いが「要素の重複回数」を考慮する点が異なる。  
**事故リスク**: 中。`namedtuple` が `tuple` のサブクラスである点（インデックスアクセスが可能）は見落としやすい。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

ログ集計サービスの頻度分析モジュールを実装しようとしている。

**他フレームワークとの差異**: Django の `QuerySet.values('field').annotate(count=Count('id'))` 相当を
Python レイヤーでやる場合に `Counter` が最速。DB 集計と Python 集計の使い分けが重要。  
**nene2-python の薄さへの評価**: collections のラッパー API として自然。
`build_recent_log` のようなスライディングウィンドウヘルパーは nene2 コアに追加する価値がある。  
**本番投入可能性**: `Counter` + `diff_counters` のパターンはイベントログ差分分析に即座に使える。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

コードレビューで `collections` の使用箇所を確認しようとしている。

**コードレビューチェックポイント**:
- [ ] `defaultdict` の返却が `dict` に変換されているか（Pydantic 互換確認）
- [ ] `deque.popleft()` / `pop()` の前に `if dq:` チェックがあるか
- [ ] `Counter` の `-` 演算で意図した結果（0 以下除去）を理解しているか
- [ ] `namedtuple` が API レスポンスとして直接使われていないか（型安全でない）
- [ ] `deque(maxlen=...)` の上限が設定されているか（リソース消費防御）

**チームでの安全なパターン**:
1. `namedtuple` → 内部処理のみ。API レスポンスは `dataclass(frozen=True, slots=True)`
2. `defaultdict` → `dict(...)` 変換後に返却
3. `Counter` の差分演算 → `a - b` は 0 以下除去を明示的にコメントで記載

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高。全エンドポイントで `max_length` 制限・`response_model` 明示・`ValidationException` を適切に使用。  
**「初心者でも安全な API」達成度**: 高。`namedtuple` を API 境界から隔離し、`dataclass` で型安全を担保する設計パターンを示せた。  
**設計上の負債**: なし（今 FT では修正不要）。  
**Follow-up Issue 候補**: `build_recent_log` のようなスライディングウィンドウヘルパーを nene2 コアに追加（優先度: 低）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 低 | `build_recent_log` スタイルのリングバッファヘルパーを nene2 コアに追加検討 | enhancement |

---

## まとめ

`collections` の 4 クラスはそれぞれ明確なユースケースがあり、API 実装に自然に統合できた。

最大の学習ポイントは:
1. **`namedtuple` は型安全でない** — API 境界は `dataclass(frozen=True, slots=True)` で守る
2. **`Counter` の `-` 演算は 0 以下を除去する** — 負値が必要なら `Counter.subtract()` を使う
3. **`deque(maxlen=N)` はリングバッファ** — 最新 N 件保持のログバッファとして最適
4. **`deque.pop()` は空チェックが必要** — `if dq:` で `IndexError` を回避する

次の FT208 は `208 % 3 = 1` → セキュリティ診断なし、`208 % 4 = 0` → クラッカーペンテストあり。
