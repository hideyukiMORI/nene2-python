# FT191: concurrent.futures モジュール

**日付**: 2026-05-21
**テーマ**: ThreadPoolExecutor / ProcessPoolExecutor / Future — 高レベル並行処理 API
**セキュリティ診断**: なし（191 % 3 = 2）

---

## 概要

`concurrent.futures` は threading と multiprocessing の上に薄い高レベル API を提供する stdlib モジュール。`ThreadPoolExecutor` / `ProcessPoolExecutor` を同一インターフェースで操作でき、`Future` オブジェクトで非同期タスクを管理できる。

本 FT では `.map()` / `.submit()` / `as_completed()` / `wait()` / タイムアウト / キャンセル / エラーハンドリングを FastAPI エンドポイントから検証する。FT188（threading）・FT189（subprocess）・FT190（multiprocessing）の高レベル抽象として位置付ける。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft191-concurrent-futures/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `thread_pool_map(values, workers)` | ThreadPoolExecutor.map で並列二乗 |
| `thread_pool_submit(values, workers)` | ThreadPoolExecutor.submit で Future 取得 |
| `thread_as_completed(values, workers)` | as_completed で完了順に収集 |
| `thread_wait_all_completed(values, workers)` | wait(ALL_COMPLETED) |
| `thread_wait_first_completed(values, workers)` | wait(FIRST_COMPLETED) |
| `thread_wait_first_exception(values, workers)` | wait(FIRST_EXCEPTION) |
| `batch_with_error_handling(values, workers)` | 例外を握りつぶさず成功/失敗分類 |
| `process_pool_map(values, workers)` | ProcessPoolExecutor.map で CPU バウンド |
| `process_pool_submit(values, workers)` | ProcessPoolExecutor.submit |
| `process_as_completed(values, workers)` | ProcessPoolExecutor + as_completed |
| `submit_with_timeout(seconds, timeout)` | タイムアウト付き Future |
| `submit_and_cancel(values)` | キャンセル試行 |
| `thread_map_with_chunksize(values, chunksize, workers)` | チャンクサイズ指定 map |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/futures/thread-map` | ThreadPoolExecutor.map |
| POST | `/futures/thread-submit` | submit で Future 取得 |
| POST | `/futures/thread-as-completed` | as_completed |
| POST | `/futures/thread-wait-all` | wait(ALL_COMPLETED) |
| POST | `/futures/thread-wait-first` | wait(FIRST_COMPLETED) |
| POST | `/futures/thread-wait-exception` | wait(FIRST_EXCEPTION) |
| POST | `/futures/batch-errors` | エラーハンドリング付きバッチ |
| POST | `/futures/process-map` | ProcessPoolExecutor.map |
| POST | `/futures/process-submit` | ProcessPoolExecutor.submit |
| POST | `/futures/process-as-completed` | ProcessPoolExecutor + as_completed |
| POST | `/futures/timeout` | タイムアウト付き Future |
| POST | `/futures/chunksize` | チャンクサイズ指定 |
| POST | `/futures/cancel` | キャンセル試行 |
| GET | `/futures/info` | 実行環境情報 |

---

## テスト結果

**51 passed**

```
51 passed in 10.86s
```

---

## 摩擦ポイント

### F-1: `submit_and_cancel` の戻り値型 `dict[str, int]` が `dict[str, object]` に非互換（深刻度: 低）

**事象**: `submit_and_cancel()` が `dict[str, int]` を返し、エンドポイントの戻り値型 `dict[str, object]` に対して mypy --strict が `Incompatible return value type` エラーを出した。

**原因**: mypy では `dict[str, int]` は `dict[str, object]` の部分型でない（`dict` は invariant）。TS の `Record<string, number>` を `Record<string, unknown>` に代入できないのと同じ理屈。

**対応**: `submit_and_cancel` の戻り値型を `dict[str, object]` に変更。戻り値の幅を広げても型安全性は失われない（返す値はすべて `int`）。

---

## 観察点

### 観察1: ThreadPoolExecutor vs ProcessPoolExecutor の使い分け

```python
# I/O バウンド → ThreadPoolExecutor（GIL 解放待ちの間に他スレッドが走る）
with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(fetch_url, urls))

# CPU バウンド → ProcessPoolExecutor（GIL を完全に回避）
with ProcessPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(heavy_compute, values))
```

threading と multiprocessing の低レベル API と同一の選択基準だが、インターフェースが統一されているため交換が容易。

### 観察2: as_completed vs map の選択

```python
# map: 送信順で結果が返る（遅いタスクがブロック）
results = list(executor.map(func, values))

# as_completed: 完了順で返る（高速タスクの結果を先に処理可能）
for future in as_completed(futures):
    result = future.result()
    process_early(result)
```

HTTP API でストリームレスポンスを返す場合や、部分結果を早期返却する設計では `as_completed` が有利。

### 観察3: wait() の return_when フラグ

| フラグ | 用途 |
|---|---|
| `ALL_COMPLETED` | 全タスク完了を待つ（デフォルト） |
| `FIRST_COMPLETED` | 最初のタスクが終わったら戻る |
| `FIRST_EXCEPTION` | 最初の例外発生で戻る（残タスクはキャンセルしない） |

`FIRST_EXCEPTION` は例外をすぐ検知したいが残タスクは並行継続したい場合に使う。

### 観察4: Future.cancel() の制約

`cancel()` はタスクが**まだ実行開始されていない**場合のみ成功する。既に実行中のタスクはキャンセルできない（Python の Future はキャンセル可能 Flag のみで、OS レベルのプロセス終了は行わない）。max_workers=1 でタスクを大量投入した場合のみキャンセルが効果的。

---

## nene2-python フレームワークとの統合

- `ThreadPoolExecutor` は I/O バウンド UseCase（外部 API 並列呼び出し等）に適用可能。ただし FastAPI はデフォルト非同期（asyncio）であり、重い I/O は `httpx.AsyncClient` での `asyncio.gather` が自然な選択
- `ProcessPoolExecutor` は CPU バウンド変換処理（画像変換・暗号化・データ集計）を同期 UseCase として切り出す際に使う
- `max_workers` の上限制限は DoS 防止のために必須。`min(workers, MAX_WORKERS)` パターンを全関数で適用
- ProcessPoolExecutor のワーカー関数も multiprocessing と同様 pickle 可能なモジュールレベル関数に限定される（FT190 F-1 と同じ制約）

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

threading/multiprocessing を学んだ後、高レベル API として concurrent.futures を使おうとしている段階。

**ドキュメント理解**: `with ThreadPoolExecutor() as executor: executor.map(func, data)` のパターンは直感的で理解しやすい。`as_completed`・`wait` は公式ドキュメントの例が豊富で困らない。`FIRST_EXCEPTION` フラグの意味は名前から推測できる。  
**事故リスク**: 低。エラーハンドリングを省略すると `future.result()` で例外が再 raise されるため、未処理の例外は実行時に気づける。  
**規約の使いやすさ**: `with executor:` の `with` ブロックは必須習慣で、抜け漏れ時は executor が自動終了するため安全。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存スクリプトの `for` ループを並列化したくてコピーして使うスタイル。

**コピペ可能性**: `executor.map(func, data)` のサンプルはそのままコピーして動く。`as_completed` のパターンも明確。  
**拡張時の罠**: ProcessPoolExecutor でラムダを渡すと PicklingError（FT190 F-1 の再現）。threading でも同じコードで動くため気づきにくい。  
**セキュリティ的な事故リスク**: 中。`max_workers` に上限がないと DoS につながる。本実装では `MAX_WORKERS = 8` で制限。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JavaScript の `Promise.all` / `Promise.race` との比較で理解しようとしている段階。

**エラーレスポンスの質**: `batch_with_error_handling` パターンで成功/失敗を分けて返すと、クライアントが部分成功を処理しやすい。422 バリデーションエラーは自動返却される。  
**Python 固有概念の学習コスト**: `Future` は JS の `Promise` に近い。`as_completed` は `Promise.race` の複数解決版として理解できる。`wait(FIRST_COMPLETED)` が `Promise.race`、`wait(ALL_COMPLETED)` が `Promise.all` に相当する。  
**事故リスク**: 低。HTTP 入力のバリデーションが Pydantic で保護されている。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

asyncio vs concurrent.futures の使い分けを判断する立場。

**他フレームワークとの差異**: FastAPI は async/await が基本なので、I/O 並列は `asyncio.gather` が自然な選択。`concurrent.futures` は CPU バウンドと、非同期対応していないレガシーライブラリの同期 I/O をスレッドプールで包む用途に限定される。`loop.run_in_executor()` で asyncio と統合できる。  
**nene2-python の薄さへの評価**: UseCase 層が HTTP 非依存なので、`ThreadPoolExecutor` を UseCase 内で直接使う設計も許容される。ただし `asyncio` 移行を前提とする場合は技術的負債になりやすい。  
**本番投入可能性**: チームが asyncio に慣れているなら concurrent.futures は補助的な役割に留めるべき。混在するとコードの可読性が下がる。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

コードレビューで concurrent.futures の誤用を検出する立場。

**コードレビューチェックポイント**:
- [ ] `max_workers` に上限制限があるか（無制限はリソース枯渇）
- [ ] `with executor:` のコンテキストマネージャーを使っているか（`executor.shutdown()` の漏れ防止）
- [ ] ProcessPoolExecutor のワーカー関数がモジュールレベルか（PicklingError 防止）
- [ ] `future.result()` の例外ハンドリングが書かれているか（未処理は実行時エラーが伝播する）
- [ ] タイムアウトが指定されているか（`future.result(timeout=N)` や `wait(timeout=N)`）

**チームでの安全な共有パターン**: ワーカー関数を `_workers.py` に分離する規則を設けると、pickle 可能性と単体テスト可能性が高まる。  
**ツール追加の必要性**: なし（ruff には concurrent.futures 固有の追加ルールはない）。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md ポリシーとの整合性を確認する。

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 高（`with executor:` がリソースリーク防止を保証、HTTP 境界の Pydantic バリデーションで DoS 制限）  
**設計上の負債・ドキュメント不足**: `asyncio` と concurrent.futures の使い分けガイドが CLAUDE.md に不足。FastAPI アプリでは asyncio が優先される旨を追記する価値がある。  
**Follow-up Issues**: なし（即時対応済み）

---

## Follow-up Issues

### 即時対応済み

| 対応内容 | 対応方法 |
|---|---|
| `dict[str, int]` を `dict[str, object]` に変更（F-1） | `submit_and_cancel` の戻り値型を修正 |

### 新規 Issue

なし（セキュリティ診断なし、全問題は即時解決済み）

---

## まとめ

concurrent.futures の主要パターン（ThreadPoolExecutor / ProcessPoolExecutor・submit / map / as_completed / wait・タイムアウト・キャンセル・エラーハンドリング）を 14 エンドポイント・51 テストで検証した。FT191 固有の発見は 1 点: `dict[str, int]` → `dict[str, object]` の invariant 問題（mypy --strict 即時検出）。

threading（FT188）・multiprocessing（FT190）の高レベル API として concurrent.futures は使いやすく、処理系（スレッド/プロセス）の交換コストが低い。FastAPI + asyncio 環境では補助的な位置付けになるが、CPU バウンド処理のオフロードには有効。
