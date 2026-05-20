# Field Trial 157: multiprocessing モジュール

## テーマ

`multiprocessing.Process`, `Pool`, `Queue`, `Pipe`, `Value`,
`cpu_count` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft157-multiprocessing/` に以下を実装:

- `get_cpu_count()` — `multiprocessing.cpu_count()` と `os.cpu_count()` を返す
- `run_processes()` — 複数 `Process` を起動して `Queue` で結果収集、PID の独立性を確認
- `pool_map_demo()` — `Pool.map()` で並列2乗計算
- `pool_starmap_demo()` — `Pool.starmap()` で並列加算
- `pipe_demo()` — `Pipe()` でプロセス間双方向通信
- `shared_value_demo()` — `Value` (共有メモリ) にロック付きでカウンターをインクリメント
- HTTP エンドポイント 6 本
- 23 テスト全通過（摩擦1件）

## テスト結果

初回: 1 失敗 → 修正後: 23 テスト全通過。

## Friction Points

### FP1: `forkserver` 起動方式でテスト関数内のローカル関数がピクルスできない

```python
# NG: テスト関数内のローカル関数は forkserver ではピクルス不可
def test_process_is_alive() -> None:
    def worker() -> None:  # ← ローカル関数
        q.put("done")

    p = multiprocessing.Process(target=worker)
    p.start()  # → PicklingError: Can't pickle local function
```

WSL2 + Python 3.14 では `multiprocessing` のデフォルト起動方式が
`forkserver`（または `spawn`）となっており、プロセス間でワーカー関数を
pickle でシリアライズして送信する。
テスト関数内のローカル関数は pickle できないため `PicklingError` になる。

`fork` 方式（Linux のデフォルト起動方式）ではこの問題は起きないが、
`forkserver`/`spawn` ではワーカー関数をモジュールレベルで定義する必要がある。

**対処**: テスト内のローカル関数をモジュールレベルに移動した。

```python
# OK: モジュールレベルの関数はピクルス可能
def _alive_worker(q: multiprocessing.Queue[str]) -> None:
    import time
    time.sleep(0.05)
    q.put("done")

def test_process_is_alive() -> None:
    p = multiprocessing.Process(target=_alive_worker, args=(q,))
    p.start()  # OK
```

## 観察

### O1: `multiprocessing.Pool.map()` は `threading.Pool` と同じインターフェース

```python
with multiprocessing.Pool(processes=4) as pool:
    results = pool.map(square, [1, 2, 3, 4, 5])
# → [1, 4, 9, 16, 25]
```

`Pool` はコンテキストマネージャで使う（`close()` / `terminate()` が自動で呼ばれる）。
`pool.starmap(func, [(a1,b1), (a2,b2)])` は複数引数の関数に対応。

### O2: `multiprocessing.Queue` はプロセス間安全な FIFO キュー

```python
q: multiprocessing.Queue[str] = multiprocessing.Queue()

def worker(q: multiprocessing.Queue[str], worker_id: int) -> None:
    q.put(f"result-{worker_id}")  # 別プロセスから安全に put できる

p = multiprocessing.Process(target=worker, args=(q, 1))
p.start()
p.join()
result = q.get()  # 親プロセスで受け取る
```

`threading.Queue` と異なり、プロセスをまたいで使えるが
内部でパイプとシリアライズを使うためオーバーヘッドがある。

### O3: `Pipe()` は双方向プロセス間通信チャンネル

```python
parent_conn, child_conn = multiprocessing.Pipe()

# 子プロセス側
child_conn.send("hello")
child_conn.close()

# 親プロセス側
data = parent_conn.recv()
parent_conn.close()
```

`Pipe(duplex=False)` で一方向パイプにできる。
デフォルトは双方向（`duplex=True`）。

### O4: `Value` と `Array` で共有メモリを使う

```python
shared_counter = multiprocessing.Value("i", 0)  # int 型, 初期値 0

def worker(counter: multiprocessing.Value[int]) -> None:
    with counter.get_lock():  # ロックを取得して安全にアクセス
        counter.value += 1
```

`Value` の typecode は `struct` モジュールと同じ（`"i"`: int, `"d"`: double など）。
`get_lock()` でロックを取得しないとレースコンディションが発生する。

### O5: 各プロセスは独立したメモリ空間を持つ

```python
result = run_processes(2)
result["all_different_pids"]  # → True (各プロセスが異なる PID を持つ)
```

スレッドと違い、プロセスはメモリを共有しない。
共有が必要なデータは `Queue`, `Pipe`, `Value`, `Array`, `Manager` を使う。

### O6: `forkserver` / `spawn` 方式はピクルス可能なオブジェクトしか渡せない

```python
# spawn/forkserver 方式でのワーカー関数の制約
# - モジュールトップレベルで定義された関数 → OK
# - クラスのメソッド → OK
# - lambda → NG
# - テスト関数内のローカル関数 → NG
```

WSL2 ではデフォルトが `forkserver` になる場合がある。
`fork` 方式が使えるなら問題ないが、クロスプラットフォーム互換のために
モジュールレベルの関数を使う習慣を持つのが安全。

## まとめ

FT157 は摩擦1件（`forkserver` 方式でローカル関数がピクルス不可）。
`Pool.map/starmap` は並列計算の主力、`Queue` と `Pipe` がプロセス間通信の 2 手段、
`Value/Array` が共有メモリアクセスを提供する。
ワーカー関数はモジュールレベルで定義しないと `forkserver/spawn` 方式で失敗する。
