# Field Trial 155: queue モジュール

## テーマ

`queue.Queue`, `LifoQueue`, `PriorityQueue`, `SimpleQueue`,
`put/get/put_nowait/get_nowait`, `maxsize`, `task_done/join` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft155-queue/` に以下を実装:

- `fill_and_drain()` — FIFO Queue に入れて取り出す
- `lifo_queue_demo()` — LifoQueue (スタック) で LIFO 順を確認
- `priority_queue_demo()` — PriorityQueue で優先度順に取り出す
- `simple_queue_demo()` — SimpleQueue（ロックフリー、maxsize なし）
- `put_nowait_overflow_demo()` — maxsize 超えで `queue.Full` 例外を確認
- `worker_demo()` — スレッドワーカーで `task_done/join` を使う
- HTTP エンドポイント 6 本
- 22 テスト全通過（摩擦0件）

## テスト結果

初回: 22 テスト全通過。摩擦なし。

## 摩擦なし

今回はブロッカーとなる摩擦なし。
`PriorityQueue` で `@dataclass(order=True)` を使う組み合わせが機能した。

## 観察

### O1: `queue.Queue` はスレッドセーフな FIFO キュー

```python
q: queue.Queue[str] = queue.Queue(maxsize=10)
q.put("item1")          # ブロッキング (満杯なら待機)
q.put_nowait("item2")   # 非ブロッキング (満杯なら queue.Full)
item = q.get()          # ブロッキング (空なら待機)
item = q.get_nowait()   # 非ブロッキング (空なら queue.Empty)
```

`maxsize=0` (デフォルト) は無制限。`q.qsize()` は近似値のためチェックより
`q.empty()` / `q.full()` を使う（ただしマルチスレッドでは競合の可能性あり）。

### O2: `LifoQueue` はスタック（後入れ先出し）

```python
q: queue.LifoQueue[int] = queue.LifoQueue()
for i in [1, 2, 3]:
    q.put(i)
[q.get() for _ in range(3)]  # → [3, 2, 1]
```

`LifoQueue` は `Queue` のサブクラスで、内部的にリストをスタックとして使う。

### O3: `PriorityQueue` は `heapq` ベースの優先度付きキュー

```python
from dataclasses import dataclass, field

@dataclass(order=True)
class PriorityItem:
    priority: int
    value: str = field(compare=False)  # priority のみ比較に使う

q: queue.PriorityQueue[PriorityItem] = queue.PriorityQueue()
q.put(PriorityItem(priority=3, value="low"))
q.put(PriorityItem(priority=1, value="high"))
q.get().value  # → "high" (優先度が小さいほど先に出る)
```

`compare=False` でサブクラスのフィールドを比較から除外できる。

### O4: `task_done()` / `join()` でワーカー完了を待機できる

```python
q = queue.Queue()
for job in jobs:
    q.put(job)

def worker():
    while True:
        job = q.get()
        process(job)
        q.task_done()  # 処理完了を通知

thread = threading.Thread(target=worker, daemon=True)
thread.start()
q.join()  # 全ての task_done() が呼ばれるまでブロック
```

`task_done()` を呼ばないと `join()` が永遠にブロックする。
`get()` した数だけ `task_done()` を呼ぶ必要がある。

### O5: `SimpleQueue` はロックフリーで maxsize なし

```python
q: queue.SimpleQueue[str] = queue.SimpleQueue()
q.put("item")
item = q.get()
```

`SimpleQueue` は `task_done/join` や `maxsize` をサポートしないが、
ロックのオーバーヘッドが少ない。単純な生産者-消費者パターンに向く。

### O6: `queue.Full` / `queue.Empty` 例外

```python
import queue

q = queue.Queue(maxsize=1)
q.put_nowait("a")
try:
    q.put_nowait("b")
except queue.Full:
    print("full!")

q2 = queue.Queue()
try:
    q2.get_nowait()
except queue.Empty:
    print("empty!")
```

`put(block=True)` はデフォルトで無制限にブロックする。
`put(block=True, timeout=1.0)` でタイムアウト付きブロッキングも可能。

## まとめ

FT155 は摩擦ゼロ。`queue` モジュールはスレッドセーフな組み込みキューを提供し、
FIFO/LIFO/優先度の 3 種類を使い分けられる。
`task_done/join` パターンが生産者-消費者の同期に使いやすく、
`SimpleQueue` はシンプルで高速なキューが必要な場合に適している。
