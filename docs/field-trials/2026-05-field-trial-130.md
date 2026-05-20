# Field Trial 130: operator モジュール + heapq + bisect の活用

## テーマ

`operator.attrgetter` によるソート、`heapq` を使った優先度キュー、
`bisect` を使ったバイナリサーチ・挿入位置探索を FastAPI エンドポイントで検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft130-operator-heapq/` に以下を実装:

- `operator.attrgetter` — 属性名でソートキーを動的に生成
- `TaskQueue` — `heapq.heappush`/`heappop`/`nsmallest` を使った優先度キュー
- `get_price_tier()` — `bisect.bisect_right` で価格帯を判定
- `find_insertion_point()` — `bisect.bisect_left` で挿入位置を取得
- `GET /products` — attrgetter でソート、カテゴリフィルター
- `POST /tasks` — heapq にタスク追加
- `GET /tasks/next` — heapq.heappop で最高優先度タスク取得
- `GET /tasks/top/{n}` — heapq.nsmallest で上位N件確認
- `GET /price-tier/{price}` — bisect で価格帯判定
- `POST /prices/insert-point` — bisect_left で挿入位置
- 22 テスト通過

## テスト結果

全 22 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `operator.attrgetter` でソートキーを文字列から動的に生成できる

```python
SORT_KEYS = {
    "price": operator.attrgetter("price"),
    "rating": operator.attrgetter("rating"),
}

# sorted() の key 引数に渡せる
sorted(products, key=SORT_KEYS["price"])
```

`lambda p: p.price` より `attrgetter("price")` のほうが文字列キーにマッピングしやすく、
dict に入れて動的ディスパッチできる。`itemgetter` は dict/タプルのキーアクセス用。

### O2: `heapq` は Python の最小ヒープ実装（同一優先度の FIFO も可能）

```python
@dataclass
class TaskQueue:
    _heap: list[tuple[int, int, str]] = field(default_factory=list)
    _counter: int = 0

    def push(self, priority: int, task: str) -> None:
        # (priority, counter, task) で同一優先度の FIFO を保証
        heapq.heappush(self._heap, (priority, self._counter, task))
        self._counter += 1
```

タプルの比較は先頭要素から順に行われる。同一 priority でも `_counter` (FIFO 順)
で順序が決まるため、同優先度のタスクは挿入順に処理される。

`heapq` は最小ヒープなので小さい数字 = 高優先度。最大ヒープが必要なら `-priority` を使う。

### O3: `bisect` でソート済みリストへの高速な位置検索ができる

```python
PRICE_TIERS = [500, 1000, 2000, 5000]
TIER_LABELS = ["budget", "standard", "premium", "luxury", "ultra-luxury"]

def get_price_tier(price: int) -> str:
    idx = bisect.bisect_right(PRICE_TIERS, price)
    return TIER_LABELS[idx]

get_price_tier(300)   # "budget"   (idx=0, < 500)
get_price_tier(500)   # "standard" (idx=1, 500 は bisect_right で右側)
get_price_tier(3000)  # "luxury"   (idx=3, 2000-4999)
```

`bisect_right(list, x)` は x と等しい要素の右側に挿入する位置を返す。
境界値のラベル割り当てには `bisect_right` か `bisect_left` かを意識して選ぶ。

## まとめ

FT130 は摩擦ゼロ確認。`operator`, `heapq`, `bisect` の組み合わせで
ソート・優先度管理・バイナリサーチが効率よく実装できることを確認した。
特に `heapq` の同優先度 FIFO 保証パターン（カウンターを使ったタプル比較）は
実用的な実装例として記録する。
