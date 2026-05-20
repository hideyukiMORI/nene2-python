# Field Trial 139: concurrent.futures + threading の活用

## テーマ

`ThreadPoolExecutor`, `as_completed`, `threading.Lock`, `threading.RLock` を使った
並行処理・スレッドセーフなデータ構造を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft139-concurrent-futures/` に以下を実装:

- `ThreadSafeCounter` — `threading.Lock` を使ったスレッドセーフなカウンター
- `run_tasks_parallel()` — `ThreadPoolExecutor` + `as_completed` で並行実行
- `run_tasks_with_timeout()` — `future.result(timeout=N)` でタイムアウト付き実行
- `ReadWriteCache` — `threading.RLock` を使ったキャッシュ
- 各 HTTP エンドポイント（カウンター、並行タスク、キャッシュ）
- 20 テスト通過（摩擦ゼロ）

## テスト結果

全 20 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `ThreadPoolExecutor` + `as_completed` で並行 I/O 処理が書ける

```python
with ThreadPoolExecutor(max_workers=4) as executor:
    future_to_id = {
        executor.submit(io_task, task_id): task_id
        for task_id, task in enumerate(tasks)
    }
    for future in as_completed(future_to_id):
        result = future.result()
        # 完了した順に処理される
```

`as_completed` は最初に完了した Future から yield する。
`executor.map()` は送信順に結果を返す（遅いタスクが前にあると後続を待つ）。
`as_completed` は完了順に処理できるため、タイムアウト管理と相性が良い。

### O2: `future.result(timeout=N)` でタイムアウト付きの結果取得ができる

```python
for future in futures:
    try:
        result = future.result(timeout=1.0)  # 1秒でタイムアウト
    except TimeoutError:
        result = {"status": "timeout"}
```

タイムアウトしても Future はキャンセルされない（バックグラウンドで実行継続）。
`executor.shutdown(wait=False)` や `future.cancel()` は最善努力のみ。

### O3: `threading.Lock` でスレッドセーフなカウンターが実装できる

```python
@dataclass
class ThreadSafeCounter:
    _count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def increment(self) -> int:
        with self._lock:
            self._count += 1
            return self._count
```

100スレッドから同時にインクリメントしてもカウントが正確に 100 になることを確認。
`int += 1` 単体は GIL があっても安全ではないため（GIL はバイトコード単位で解放される）、
`Lock` で保護が必要。

### O4: FastAPI の `async def` ハンドラーは同期コードをスレッドプールで実行する

FastAPI/Starlette は `sync def` ルートハンドラーを自動的にスレッドプールで実行するため、
`ThreadPoolExecutor` 内で `time.sleep` などのブロッキング処理をしても
メインの async イベントループをブロックしない。

## まとめ

FT139 は摩擦ゼロ確認。`ThreadPoolExecutor` + `as_completed` によるI/Oバウンド並行処理と
`threading.Lock`/`RLock` によるスレッドセーフなデータ構造を FastAPI で確認した。
CPU バウンドな並行処理は `ProcessPoolExecutor` を使うべき（GIL の影響を受けないため）。
