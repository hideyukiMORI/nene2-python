# Field Trial 156: threading モジュール

## テーマ

`threading.Thread`, `Lock`, `RLock`, `Event`, `Condition`, `Barrier`,
`threading.local()` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft156-threading/` に以下を実装:

- `run_threads_and_collect()` — 複数スレッドを起動して `Lock` で結果を収集
- `counter_with_lock()` — `Lock` でスレッドセーフなカウンターをインクリメント
- `rlock_reentrant_demo()` — `RLock` が同一スレッドから再取得できることを確認
- `event_signaling_demo()` — `Event` でスレッド間シグナルを送受信
- `condition_producer_consumer_demo()` — `Condition` で生産者-消費者パターン
- `barrier_demo()` — `Barrier` で全スレッドが揃ってから次に進む
- `thread_local_demo()` — `threading.local` でスレッドごとの独立した値を持つ
- HTTP エンドポイント 7 本
- 24 テスト全通過（摩擦1件）

## テスト結果

初回: 1 失敗 → 修正後: 24 テスト全通過。

## Friction Points

### FP1: `threading.local` の辞書キーは Python 呼び出し時は int、HTTP 経由では str

```python
def thread_local_demo(thread_count: int) -> dict[str, Any]:
    results: dict[int, int] = {}

    def worker(thread_id: int) -> None:
        _thread_local.value = thread_id * 10
        results[thread_id] = _thread_local.value  # キーは int

    ...
    return {"results": results, ...}

# 直接呼び出し → results[0], results[1] (int キー)
# HTTP 経由 → JSON シリアライズで "0", "1" (str キー)
```

テストで `result["results"]["0"]` と書いたが、直接関数呼び出し時は
`dict[int, int]` なので `result["results"][0]` でないとキーエラーになる。

**対処**: テストを `result["results"][0]` (int キー) に修正した。
HTTP エンドポイント経由では JSON が `"0"` など文字列キーに変換されるが、
直接関数呼び出しでは `int` キーのまま。

## 観察

### O1: `threading.Lock()` はコンテキストマネージャで使う

```python
lock = threading.Lock()
with lock:
    shared_resource.modify()
# ブロック終了で自動 release
```

`with lock:` は `lock.acquire()` / `lock.release()` と同等。
例外が起きても確実に release される。

### O2: `RLock` は同一スレッドから複数回 acquire できる

```python
rlock = threading.RLock()
with rlock:
    # 同一スレッドから再度取得可能
    acquired = rlock.acquire(blocking=False)  # → True
    if acquired:
        rlock.release()

# 通常 Lock では同一スレッドから再取得するとデッドロック
```

再帰的な関数でロックを使う場合は `RLock` を使う。

### O3: `Event` はシンプルなシグナリング機構

```python
event = threading.Event()

def waiter():
    event.wait(timeout=5.0)  # セットされるまでブロック
    if event.is_set():
        print("received!")

event.set()    # 全ての wait をアンブロック
event.clear()  # リセット
```

### O4: `Condition` で複雑な待機条件を記述できる

```python
condition = threading.Condition()

# 生産者
with condition:
    buffer.append(item)
    condition.notify()  # 1つのウェイターを起こす

# 消費者
with condition:
    condition.wait_for(lambda: bool(buffer))
    item = buffer.pop(0)
```

`notify_all()` で全ウェイターを起こす。
`wait_for(predicate)` はスプリアスウェイクアップを自動で処理する。

### O5: `Barrier` で全スレッドの同期点を作れる

```python
barrier = threading.Barrier(3)  # 3スレッドが揃うまで待機

def worker():
    # ... 前処理 ...
    barrier.wait()  # 全スレッドが到達するまでブロック
    # ... 後処理（全員揃ってから始まる）...
```

### O6: `threading.local()` はスレッドごとの独立した名前空間

```python
_local = threading.local()

def worker(thread_id: int) -> None:
    _local.value = thread_id  # このスレッドだけに見える
    time.sleep(0.1)
    print(_local.value)  # → thread_id (他スレッドの変更に影響されない)
```

FastAPI のリクエストスコープのコンテキスト変数として使えるが、
ASGI は通常 asyncio を使うため `threading.local` よりも
`contextvars.ContextVar` が適している。

## まとめ

FT156 は摩擦1件（`threading.local` の辞書キーが直接呼び出し時 `int`、
HTTP 経由 JSON で `str` になる非対称）。
`Lock/RLock/Event/Condition/Barrier/threading.local` がすべて機能した。
ASGI フレームワーク (FastAPI) では `contextvars` の方が適しているが、
バックグラウンドスレッドでは `threading.local` が有用。
