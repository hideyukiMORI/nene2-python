# Field Trial 141: asyncio 高度機能

## テーマ

`asyncio.Queue`, `asyncio.Lock`, `asyncio.Event`, `asyncio.Semaphore`,
`asyncio.TaskGroup`, `asyncio.wait_for`, `asyncio.as_completed` を
FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft141-asyncio-advanced/` に以下を実装:

- `AsyncJobQueue` — `asyncio.Queue` でプロデューサー・コンシューマーパターン
- `AsyncCounter` — `asyncio.Lock` (`async with`) でスレッドセーフカウンター
- `AsyncEventBus` — `asyncio.Event` でイベント通知・待機
- `fetch_many()` — `asyncio.Semaphore` で最大並行数を制限したバッチフェッチ
- `run_with_task_group()` — `asyncio.TaskGroup` (Python 3.11+) で構造化並行実行
- `run_with_timeout()` — `asyncio.wait_for` でタイムアウト付き実行
- `run_as_completed()` — `asyncio.as_completed` で完了順処理
- 対応 HTTP エンドポイント
- 27 テスト通過（摩擦2件あり）

## テスト結果

初回: 12失敗 → 修正後: 27テスト全通過。

## Friction Points

### FP1: `anyio[trio]` を依存に含めると asyncio プリミティブのテストが trio バックエンドでも実行されて失敗する

`pytest-asyncio` の代わりに `anyio[trio]` を依存に追加したため、
`@pytest.mark.anyio` デコレータが asyncio バックエンドと trio バックエンドの両方でテストを実行した。
`asyncio.Lock`, `asyncio.Event`, `asyncio.Semaphore` は asyncio 専用プリミティブのため、
trio バックエンドでは `RuntimeError: no running event loop` が発生した。

**対処**: `anyio[trio]` を `pytest-asyncio>=0.23.0` に置き換え、
`@pytest.mark.anyio` を `@pytest.mark.asyncio` に変更した。

### FP2: モジュールレベルで生成した `asyncio.Semaphore` は別イベントループで使うと失敗する

```python
# 問題のあるコード
_semaphore = asyncio.Semaphore(3)  # モジュールロード時に生成

async def limited_fetch(item_id: int) -> dict[str, object]:
    async with _semaphore:  # 別ループで使うと RuntimeError
        ...
```

TestClient がエンドポイントを呼び出すと、`_semaphore` が生成された時の
イベントループと異なるループで実行されるため
`RuntimeError: bound to a different event loop` が発生した。

**対処**: Semaphore を関数スコープで生成するように変更した。

```python
async def fetch_many(item_ids: list[int], max_concurrent: int = 3) -> ...:
    semaphore = asyncio.Semaphore(max_concurrent)  # 呼び出しごとに生成

    async def limited_fetch(item_id: int) -> ...:
        async with semaphore:
            ...
```

## 観察

### O1: `asyncio.Lock` は `async with` で使う（`with` 不可）

```python
@dataclass
class AsyncCounter:
    _count: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def increment(self) -> int:
        async with self._lock:   # async with のみ有効
            self._count += 1
            return self._count
```

`threading.Lock` は `with` だが、`asyncio.Lock` は `async with`。
`asyncio.gather()` で並行インクリメントしても正確にカウントされる。

### O2: `asyncio.TaskGroup` で構造化並行処理ができる（Python 3.11+）

```python
async with asyncio.TaskGroup() as tg:
    for i, d in enumerate(durations):
        tg.create_task(task(i, d))
# ← ここで全タスクが完了するまでブロック
```

`asyncio.gather()` と違い、いずれかのタスクが例外を投げると
グループ内の全タスクがキャンセルされる（構造化並行処理）。

### O3: `asyncio.wait_for` でタイムアウト付き実行ができる

```python
try:
    result = await asyncio.wait_for(slow_operation(delay), timeout=timeout)
    return {"result": result, "timed_out": False}
except TimeoutError:
    return {"result": None, "timed_out": True}
```

タイムアウト時は `TimeoutError` が発生する（Python 3.11+ からは `asyncio.TimeoutError` ではなく組み込みの `TimeoutError`）。

### O4: `asyncio.as_completed` は完了順に結果を返す（元の順序と異なる場合がある）

```python
tasks = [asyncio.create_task(task(i, d)) for i, d in enumerate(durations)]
for coro in asyncio.as_completed(tasks):
    result = await coro
    results.append(result)
# results の順序は完了が速い順 — 元の index 順ではない
```

`asyncio.gather()` が元の順序を保持するのと対照的。
早く完了したタスクから処理したい場合（ストリーミング、最初の結果を早く返す等）に有効。

### O5: `dataclass` フィールドで asyncio プリミティブを生成するには `field(default_factory=...)` を使う

```python
@dataclass
class AsyncCounter:
    _count: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
```

`asyncio.Lock = asyncio.Lock()` のようにデフォルト値で直接インスタンス生成すると
全インスタンスで同じオブジェクトを共有する。`field(default_factory=...)` で
インスタンスごとに新しいロックを生成する。

## まとめ

FT141 は摩擦2件（anyio/trio 混入によるバックエンド非互換、
モジュールレベル asyncio プリミティブのイベントループ問題）。
`asyncio.TaskGroup` による構造化並行処理と `asyncio.wait_for`/`as_completed` の
使い分けを FastAPI エンドポイントで確認した。
