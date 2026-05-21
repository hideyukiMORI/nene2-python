# FT190: multiprocessing モジュール

**日付**: 2026-05-21
**テーマ**: プロセスベース並行処理・共有状態・プロセスプール
**セキュリティ診断**: なし（190 % 3 = 1）

---

## 概要

`multiprocessing` は threading と異なりプロセスを分離して実行するため、GIL（Global Interpreter Lock）の影響を受けず CPU バウンドタスクの並列化に有効。本 FT では `Pool.map` / `Pool.starmap` / `Pool.imap` / `Pool.apply_async`・共有メモリ（`Value`）・プロセス間キュー（`Queue`）・初期化関数付きプールなどの主要パターンを FastAPI エンドポイントから検証する。

FT188（threading）・FT189（subprocess）の直後として、プロセスベース並行処理の違いと型安全上の注意点を記録することも目的とする。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft190-multiprocessing/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `spawn_process(name)` | 単一プロセスを起動して PID・Alive 状態を返す |
| `pool_map(values, workers)` | Pool.map で並列二乗計算 |
| `pool_map_cube(values, workers)` | Pool.map で並列三乗計算 |
| `pool_starmap(pairs, workers)` | Pool.starmap で並列加算 |
| `apply_async_demo(values, delay)` | apply_async で非同期タスク |
| `shared_counter_demo(num_processes, increments_each)` | Value + Lock で共有カウンター |
| `queue_producer_consumer(items)` | Queue でプロデューサー/コンシューマー |
| `pool_imap_ordered(values, workers)` | Pool.imap（順序保証） |
| `pool_imap_unordered(values, workers)` | Pool.imap_unordered（順序不定） |
| `pool_map_chunksize(values, chunksize, workers)` | チャンクサイズ付き Pool.map |
| `pool_with_initializer(values, config)` | 初期化関数付き Pool |
| `build_task_func(operation)` | 操作名から関数を返す（match 文使用） |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/multiprocessing/spawn` | プロセス起動・PID 取得 |
| GET | `/multiprocessing/cpu-count` | CPU コア数・start method |
| POST | `/multiprocessing/pool-map` | 並列二乗計算 |
| POST | `/multiprocessing/pool-map-cube` | 並列三乗計算 |
| POST | `/multiprocessing/pool-starmap` | 並列加算 |
| POST | `/multiprocessing/apply-async` | 非同期タスク |
| POST | `/multiprocessing/shared-counter` | 共有カウンター（Lock 付き） |
| POST | `/multiprocessing/queue` | プロデューサー/コンシューマー |
| POST | `/multiprocessing/imap-ordered` | 順序保証 imap |
| POST | `/multiprocessing/imap-unordered` | 順序不定 imap |
| POST | `/multiprocessing/chunksize` | チャンクサイズ指定 map |
| POST | `/multiprocessing/with-initializer` | 初期化関数付きプール |
| GET | `/multiprocessing/daemon-demo` | デーモンプロセスデモ |

---

## テスト結果

**56 passed**

```
56 passed in 1.18s
```

---

## 摩擦ポイント

### F-1: Pool.starmap にローカル関数を渡すと PicklingError（深刻度: 中）

**事象**: `pool_starmap()` 内でローカル関数 `add` を定義して `pool.starmap(add, pairs)` に渡したところ、`_pickle.PicklingError: Can't pickle local object` が発生した。

**原因**: multiprocessing はワーカープロセスにタスクを pickle で送信する。ローカル関数はモジュールトップレベルに存在しないため、ワーカーが unpickle できない。threading ではそのまま渡せるため、つい同じように書いてしまう。

**対応**: `_add(a, b)` としてモジュールレベルに定義。ワーカー用関数は必ずモジュールレベルに置くルールを確認（threading と multiprocessing の違い）。

### F-2: `multiprocessing.Value` に `Synchronized[c_int]` を使うと mypy エラー（深刻度: 低）

**事象**: `counter: Synchronized[c_int] = Value(c_int, 0)` と書くと、`counter.value += 1` に対して `Unsupported operand types for + ("c_int" and "int")` エラーが発生した。

**原因**: typeshed の `Synchronized[_CT]` は `.value` を `_CT` 型として定義しており、`_CT = c_int` のとき `c_int + int` が不正になる。しかし実際の runtime では `Value("i", 0).value` は Python の `int` を返す。型スタブが実態と乖離している。

**対応**: `Synchronized[int]` とアノテーションし `Value("i", 0)` (文字列フォーマットコード) を使用。mypy は文字列フォーマットコードからジェネリック型を解決できないため `Synchronized[int]` の明示アノテーションで型整合が取れる。

---

## 観察点

### 観察1: Pool ワーカー関数のスコープ制約

multiprocessing の Pool ワーカーは pickle でシリアライズしてワーカープロセスに送信する。pickle できるのはモジュールトップレベルで定義された関数のみ。lambda・クロージャ・ローカル関数は pickle できない。

```python
# ❌ PicklingError
def my_func(pairs):
    def add(a, b): return a + b
    with Pool() as pool:
        return pool.starmap(add, pairs)

# ✅ 正しい
def _add(a: int, b: int) -> int:  # モジュールレベル
    return a + b

def my_func(pairs):
    with Pool() as pool:
        return pool.starmap(_add, pairs)
```

### 観察2: GIL と multiprocessing

threading では GIL により Python バイトコードの並列実行が制限される（I/O バウンドは並行可）が、multiprocessing は別プロセスなので GIL を回避して CPU バウンドタスクを並列化できる。プロセス起動コスト（～50ms）があるため、軽量タスクには Pool よりも threading が適する。

### 観察3: Value の型アノテーション戦略

```python
# 実態と合うアノテーション
from multiprocessing.sharedctypes import Synchronized
counter: Synchronized[int] = Value("i", 0)  # 文字列フォーマットコードを使う
```

`Synchronized[int]` とすることで `counter.value` が `int` として扱われ、`counter.value += 1` が mypy --strict を通過する。`Value(c_int, 0)` の形式は typeshed との不整合を生む。

---

## nene2-python フレームワークとの統合

- Pool ワーカー関数はモジュールレベルに置く制約があるため、プロセスプールを使う UseCase では関数をモジュールレベルの `_private` 関数として分離するパターンが必要
- FastAPI のリクエストハンドラー内で `Pool` を生成する場合、`with Pool() as pool:` のコンテキストマネージャーで確実にクリーンアップすること（`pool.terminate()` の漏れ防止）
- multiprocessing は `__main__` ガード（`if __name__ == "__main__":`）が必要な start method（spawn/forkserver）があるが、FastAPI アプリとして使う場合は `fork`（Linux デフォルト）なので不要。ただし Windows 移植時は注意
- `MAX_WORKERS: int = 8` 定数でワーカー数を上限制限し、DoS を防止

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

チュートリアルで threading を学んだ後、multiprocessing に入門する段階。

**ドキュメント理解**: `Pool.map` の使い方は直感的で理解しやすい。ワーカー関数がモジュールレベルでないと `PicklingError` になる制約は、threading と混同して気づきにくい（F-1）。エラーメッセージが英語で `Can't pickle local object` と出るので原因の特定は可能だが、初心者には意味が分かりにくい。  
**事故リスク**: 中。PicklingError は実行時エラーで早期発見できるが、初心者が「なぜ動かないのか」を理解するまでに時間がかかる。  
**規約の使いやすさ**: `with Pool(processes=n) as pool:` のパターンは覚えやすい。ワーカー関数をモジュールレベルに置く規則は一度理解すれば機械的に適用できる。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

threading コードをコピーして multiprocessing に変えようとする場面。

**コピペ可能性**: `Pool.map` のサンプルは分かりやすい。ただし、ラムダや内側クロージャを気軽に使うと PicklingError になる。threading では動いたコードをそのまま転用できないケースがある。  
**拡張時の罠**: `Value("i", 0)` の型アノテーションを `Synchronized[c_int]` と書くと mypy エラーになる（F-2）。型を「直しよう」としてはまる。`Synchronized[int]` と書く正解はドキュメントに明示されていない。  
**セキュリティ的な事故リスク**: 中。`workers` 上限がなければ `Pool(processes=99999)` でプロセス枯渇 DoS が可能。本実装では `MAX_WORKERS = 8` で上限制限している。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

並行処理の概念（Promise.all 的なもの）はわかるが、プロセスとスレッドの違いが曖昧な段階。

**エラーレスポンスの質**: 422 Unprocessable Entity が `workers` 超過・`values` 超過で正しく返る。`PicklingError` は HTTP 500 になるが、デモコードのワーカー関数はモジュールレベルに固定しているため HTTP 経由では発生しない。  
**Python 固有概念の学習コスト**: `Pool` が Python オブジェクトプールではなくプロセスプールであること、`fork` vs `spawn` の start method の違いは非直感的。  
**事故リスク**: 低。HTTP 入力のバリデーションが Pydantic で守られており、エンドポイント経由では PicklingError には到達できない。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Celery・concurrent.futures との比較で評価する。

**他フレームワークとの差異**: `concurrent.futures.ProcessPoolExecutor` と `multiprocessing.Pool` は機能が重複する。FastAPI アプリで重い CPU 処理をオフロードするなら `ProcessPoolExecutor` の方が Python 公式の高レベル API として推奨されている。本 FT が `Pool` を選んだのは stdlib の低レベル API を直接学ぶため。  
**nene2-python の薄さへの評価**: UseCase 層が HTTP・DB 非依存なので、Pool ワーカーに UseCase を渡す設計も可能（ただし pickle 可能なオブジェクトに限る）。  
**本番投入可能性**: `MAX_WORKERS` の上限設定・`with Pool() as pool:` のコンテキスト管理が適切。本番では `ProcessPoolExecutor` との使い分けガイドが欲しい。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チームで multiprocessing を使う場合のリスクをレビューする。

**コードレビューチェックポイント**:
- [ ] `Pool.map` のワーカー関数がモジュールレベルか（ローカル関数・lambda は PicklingError）
- [ ] `with Pool() as pool:` でコンテキストマネージャーを使い、確実に終了しているか
- [ ] `workers` に上限制限があるか（`min(workers, MAX_WORKERS)` パターン）
- [ ] `join(timeout=N)` でゾンビプロセス防止が書かれているか
- [ ] `Value` の型アノテーションが `Synchronized[int]` か（`Synchronized[c_int]` は mypy 不整合）

**チームでの安全な共有パターン**: ワーカー関数ファイルを `_workers.py` として分離する規則を設けると pickle 可能性が明確になる。  
**ツール追加の必要性**: ruff には multiprocessing 固有のルールはない。`pool.map(lambda x: x, [])` のようなラムダ誤用は静的解析では検出できない（実行時エラー）。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md ポリシーとの整合性を確認する。

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 中（PicklingError は HTTP 経由では発生しないが、demos.py を直接使う場面では踏みやすい）  
**設計上の負債・ドキュメント不足**: `multiprocessing.Value` の型アノテーション方法（`Synchronized[int]` vs `Synchronized[c_int]`）が typeshed の実態と乖離している点は How-to に記録する価値がある（→ Follow-up Issue）  
**Follow-up Issues**: 下記参照

---

## Follow-up Issues

今回の FT で発見した問題を同 FT PR 内で即時対応済み（バックログを残さないルール）。

### 即時対応済み

| 対応内容 | 対応方法 |
|---|---|
| Pool.starmap にローカル関数を渡して PicklingError（F-1） | `_add()` をモジュールレベルへ移動 |
| `Synchronized[c_int]` mypy 不整合（F-2） | `Synchronized[int]` + `Value("i", 0)` に変更 |

### 文書化 Issue（同 PR で作成・クローズ）

| タイトル | 種別 |
|---|---|
| multiprocessing.Value のアノテーションには `Synchronized[int]` を使う | docs |

---

## まとめ

multiprocessing の主要パターン（Pool.map/starmap/imap/apply_async・Value・Queue・初期化関数）を 13 エンドポイント・56 テストで検証した。FT190 固有の発見は 2 点:

1. **PicklingError**: Pool ワーカー関数のモジュールレベル配置制約（threading との差異）
2. **Value 型アノテーション**: `Synchronized[c_int]` は typeshed と乖離、`Synchronized[int]` + 文字列フォーマットコードで回避

いずれも実装中に即時修正済み。FT191 に向けた懸案はなし。
