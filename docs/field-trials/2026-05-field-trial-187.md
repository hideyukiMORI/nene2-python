# FT187: collections

**日付**: 2026-05-21
**テーマ**: collections モジュール — Counter・defaultdict・deque・ChainMap・NamedTuple・OrderedDict
**セキュリティ診断**: なし（187 % 3 = 1）
**クラッカーペンテスト**: なし（187 % 4 = 3）

---

## 概要

Python 標準ライブラリ `collections` は汎用コンテナ型の拡張集である。
`Counter`（頻度カウント）、`defaultdict`（デフォルト値付き辞書）、`deque`（両端キュー）、`ChainMap`（複数辞書のビュー）、`NamedTuple`（型付き名前付きタプル）、`OrderedDict`（挿入順序保持辞書）の主要 6 型を検証した。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft187-collections/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `word_frequency(text)` | Counter で単語頻度を集計 |
| `top_n_words(text, n)` | `most_common(n)` で上位 N 単語を取得 |
| `character_frequency(text)` | 文字頻度を集計（空白除外）|
| `merge_counters(a, b)` | Counter の `+` 演算子でマージ |
| `subtract_counters(a, b)` | Counter の `-` 演算子で差分（正の値のみ）|
| `group_by_length(words)` | defaultdict でワード長別グループ化 |
| `build_inverted_index(docs)` | defaultdict で転置インデックス構築 |
| `count_nested(items, sep)` | ネスト defaultdict でカテゴリ別集計 |
| `BoundedHistory` | `deque(maxlen=N)` でサイズ制限付き履歴 |
| `sliding_window_average(values, window)` | deque + maxlen でスライディング平均 |
| `rotate_list(items, steps)` | `deque.rotate()` でリストをローテーション |
| `resolve_config(*layers)` | ChainMap で設定レイヤーを優先順解決 |
| `get_with_override(base, override, key)` | ChainMap で override 優先の値取得 |
| `Coordinate` | `typing.NamedTuple` で型付き座標 |
| `deduplicate_preserving_order(items)` | OrderedDict で順序保持重複除去 |
| `LruDict` | OrderedDict を使った LRU キャッシュ |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/counter/words` | 単語頻度集計 |
| POST | `/counter/top` | 上位 N 単語 |
| POST | `/counter/chars` | 文字頻度集計 |
| POST | `/counter/merge` | カウンターマージ |
| POST | `/counter/subtract` | カウンター差分 |
| POST | `/defaultdict/group` | 長さ別グループ化 |
| POST | `/defaultdict/index` | 転置インデックス |
| POST | `/defaultdict/nested` | ネストカウント |
| POST | `/deque/sliding-window` | スライディング平均 |
| POST | `/deque/rotate` | リストローテーション |
| POST | `/chainmap/resolve` | 設定レイヤー解決 |
| POST | `/ordereddict/deduplicate` | 順序保持重複除去 |
| POST | `/namedtuple/coordinates` | 座標パース |
| POST | `/ordereddict/lru` | LRU キャッシュ操作 |

---

## テスト結果

**56 passed**

```
56 passed in 0.35s
```

mypy --strict: Success  
ruff check: All checks passed  
pip-audit: PYSEC-2025-183 (PyJWT via mcp transitive dep — 許容済み)

---

## 摩擦ポイント

### F-1: `parse_coordinates` の引数型に `dict[str, float | str]` を使うと mypy エラー（深刻度: 低）

**事象**: `parse_coordinates(raw: list[dict[str, float | str]])` を定義し、呼び出し側で `[{"latitude": c.latitude, ...}]` を渡したところ、mypy が `Argument 1 has incompatible type "list[dict[str, object]]"` エラーを出した。辞書リテラルの型が `dict[str, object]` として推論されるため。

**原因**: Python の辞書リテラル `{"latitude": 35.0, "label": "A"}` は `dict[str, float | str]` ではなく `dict[str, object]` として推論される（値の型が異なる場合）。

**対応**: 入力専用のデータクラス `RawCoordinate(dataclass(frozen=True, slots=True))` を定義して型安全な引数にした。`dict` を渡す代わりに `RawCoordinate` オブジェクトを渡す。

```python
@dataclass(frozen=True, slots=True)
class RawCoordinate:
    latitude: float
    longitude: float
    label: str = ""

def parse_coordinates(raw: list[RawCoordinate]) -> list[Coordinate]:
    return [Coordinate(latitude=r.latitude, ...) for r in raw]
```

---

## 観察点

### 観察1: Counter の算術演算子

```python
a = Counter({"x": 5, "y": 2})
b = Counter({"x": 3, "y": 4})

a + b  # {"x": 8, "y": 6}  — 合計
a - b  # {"x": 2}           — 差分（正の値のみ残る）
a & b  # {"x": 3, "y": 2}  — 最小値（intersection）
a | b  # {"x": 5, "y": 4}  — 最大値（union）
```

`Counter` は `dict` のサブクラスで算術演算子が使えるため、集合演算的な使い方ができる。`-` の結果は正の値のみ（負になったキーは除外）になる点が直感と異なる場合がある。

### 観察2: defaultdict のネスト — `lambda` を使ったデフォルト値

```python
# ネストした defaultdict
result: defaultdict[str, defaultdict[str, int]] = \
    defaultdict(lambda: defaultdict(int))

# 使用例
result["fruit"]["apple"] += 1
```

`lambda: defaultdict(int)` でネストした自動生成が可能。ただし `lambda` の型は mypy で推論が難しいため、明示的な型注釈が必要になる場合がある。

### 観察3: deque の `maxlen` による自動エビクション

```python
dq = deque(maxlen=3)
dq.append(1)  # [1]
dq.append(2)  # [1, 2]
dq.append(3)  # [1, 2, 3]
dq.append(4)  # [2, 3, 4] — 左端の 1 が自動除去
```

`deque(maxlen=N)` は満杯時に反対側の要素を自動除去する。スライディングウィンドウ・LRU 的な「最近 N 件だけ保持」のユースケースに適している。`appendleft` を使うと最新が先頭になる（`BoundedHistory` パターン）。

### 観察4: ChainMap の「先頭優先」セマンティクス

```python
chain = ChainMap(override, base)
chain["key"]  # override の値を優先（なければ base を参照）
chain["new"] = "value"  # 先頭の override に追加（base は変更されない）
```

`ChainMap` は辞書のコピーを作らずビューを提供する。環境変数 → 設定ファイル → デフォルト値という優先順位を持つ設定解決に適している。`new_child()` で新しいスコープを作成することも可能。

### 観察5: `typing.NamedTuple` vs `collections.namedtuple`

```python
# collections.namedtuple — フィールド名のみ、型なし
Point = namedtuple("Point", ["x", "y"])

# typing.NamedTuple — 型付きフィールド、デフォルト値、メソッド定義可
class Coordinate(NamedTuple):
    latitude: float
    longitude: float
    label: str = ""
    def distance_to(self, other: "Coordinate") -> float: ...
```

`typing.NamedTuple` は型安全でデフォルト値・メソッドを持てるため、`dataclass` の代替として不変の小さな値オブジェクトに使える。ただし `frozen=True` の `dataclass` と異なり、継承で問題が生じやすいため、単純な値型に限定するのが無難。

### 観察6: OrderedDict を使った LRU キャッシュ

```python
cache = OrderedDict()

def get(key):
    cache.move_to_end(key)  # アクセスで MRU 端へ移動
    return cache[key]

def put(key, value):
    if len(cache) >= capacity:
        cache.popitem(last=False)  # LRU 端（先頭）から除去
    cache[key] = value
```

Python 3.2+ の `dict` は挿入順序保持が保証されているが、`OrderedDict` は `move_to_end()` と `popitem(last=False/True)` を持ち、LRU 実装が簡潔に書ける。

---

## Follow-up Issues

今回の FT では実装上の重大な摩擦はなかった。F-1 は mypy --strict での型推論の限界によるものであり、`dataclass` を入力型として導入することで解決した。

GitHub Issues: なし

---

## DX Review — 6ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`Counter` は「リストの頻度を数える」という非常に頻繁に必要とされる操作をワンライナーで実現できる。`most_common(n)` の使いやすさは特に印象的で、手書きのループより明快。

**ドキュメント理解**: `defaultdict` の「キーが存在しなければデフォルト値を自動生成する」という動作は、通常の辞書で `KeyError` に何度もぶつかった後に習得するパターン。デモのネスト例は実用的で理解しやすい。

**事故リスク**: 低 — ただし `Counter` の `-` が「負値を除外する」挙動を知らないと驚く。テストで明示したことで習得しやすい。

**規約の使いやすさ**: `LruDict` のパターン（`move_to_end` + `popitem`）は初心者には高度だが、「なぜ OrderedDict を使うのか」が実例で見えると理解が進む。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`Counter.most_common()` はログ解析・アクセス集計でそのまま使えるため実務価値が高い。`defaultdict(list)` による転置インデックスも業務で頻繁に必要になる。

**コピペ可能性**: `BoundedHistory`（deque + maxlen）・`LruDict`・`resolve_config`（ChainMap）はそのまま流用できるユーティリティ。

**拡張時の罠**: `ChainMap` の `chain["key"] = value` は先頭辞書のみ変更する。「両方の辞書を更新したい」場合は `ChainMap` は不適切。

**事故リスク**: 低

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript では `Map<string, number>` や `Record<string, number>` で表現するものが Python では `Counter` / `defaultdict` に対応する。`ChainMap` は TS にない概念だが、React の Context や CSS カスケードと近いセマンティクスで理解できる。

**エラーレスポンスの質**: `/deque/sliding-window` の `window=0` に対する 422 バリデーションエラーは適切。FastAPI の `Field(ge=1)` が自動で機能している。

**Python 固有概念の学習コスト**: `NamedTuple` は TypeScript のインターフェースに近い。デフォルト値・メソッド定義できる点は TS の interface と同じ感覚で理解できる。

**事故リスク**: 低

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`Counter` の算術演算子や `defaultdict` のネストは Django の `annotate()` / `aggregate()` では難しいデータ変換を純粋 Python で行う際に重宝する。`ChainMap` は Django の設定（`DJANGO_SETTINGS_MODULE` → デフォルト設定）と類似のパターン。

**他フレームワークとの差異**: `LruDict` は `functools.lru_cache` と比べて「任意の引数に対応する柔軟性」と「キャッシュの明示的管理」がメリット。

**nene2 の薄さへの評価**: `collections` は nene2 フレームワークと独立しているため、ドメインロジック層の実装にそのまま使えるコレクション群として評価が高い。

**事故リスク**: 低

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `defaultdict` が「サービス境界を超える」ケースに注意（外部に返す前に `dict(dd)` で変換しているか）
- `Counter` の `subtract()` メソッドと `-` 演算子の違い（`subtract` は負値を保持、`-` は正値のみ）
- `deque` に `maxlen` が設定されているか（無制限 deque は意図しないメモリ増大の原因）
- `ChainMap` の変更は先頭辞書のみに反映されることを把握しているか

**チームでの安全なパターン**: `BoundedHistory`（maxlen 付き deque）は監査ログ・エラー履歴の実装に、`resolve_config`（ChainMap）は設定オーバーライドに使えるチーム共有ユーティリティ。

**事故リスク**: 低

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**:
- `dataclass(frozen=True, slots=True)`: `DequeSnapshot`・`RawCoordinate` で適用済み ✅
- Pydantic は HTTP 境界のみ: `app.py` の Request/Response モデルのみ ✅
- `create_app()` はファイル末尾: 適用済み ✅（FT182 の教訓）
- `max_length` 指定: 全文字列・リストフィールドに設定済み ✅
- 型安全: `dict[str, float | str]` の問題を `RawCoordinate` dataclass で解決 ✅

**初心者でも安全な API 達成度**: `BoundedHistory` が「maxlen を必ず指定して使う」パターンを示し、`LruDict` が「容量が決まっている場合のみ OrderedDict LRU を使う」ことを Pydantic の `le=100` で強制している設計は初心者でも誤用しにくい。

---

*バージョン: v1.8.58*
