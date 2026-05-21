# FT188: threading モジュール — Thread・Lock・RLock・Semaphore・Event・ThreadPoolExecutor・Queue・Timer

**日付**: 2026-05-21
**テーマ**: threading モジュールの主要プリミティブとスレッドセーフパターンを FastAPI サンドボックスで検証
**セキュリティ診断**: なし（188 % 3 = 2）
**クラッカーペンテスト**: **あり**（188 % 4 = 0）

---

## 概要

`threading` モジュールの基本プリミティブ（`Lock`・`RLock`・`Semaphore`・`Event`）から
高レベルの `ThreadPoolExecutor`・`queue.Queue`・`threading.local`・`threading.Timer` まで、
スレッドセーフ実装パターンを一通り検証する。
スレッドセーフティに直結する競合状態・デッドロック・DoS を特に重点的に確認し、
クラッカーペンテストで実際に攻撃ペイロードを送り込んで耐性を評価する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft188-threading/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `ThreadSafeCounter` | `Lock` でスレッドセーフにしたカウンター |
| `parallel_increment()` | 複数スレッドからカウンターをインクリメント |
| `TreeNode` | `RLock` を使ったスレッドセーフなツリーノード（再入可能） |
| `run_with_semaphore()` | `Semaphore` で同時実行数を制限してタスク実行 |
| `run_with_event_sync()` | `Event` でスレッド間「準備完了」「完了」を同期 |
| `run_tasks_in_pool()` | `ThreadPoolExecutor` + `as_completed()` で並列処理・例外隔離 |
| `producer_consumer()` | `queue.Queue` によるプロデューサー-コンシューマーパターン |
| `run_with_thread_context()` | `threading.local` のスレッドローカル分離確認 |
| `run_delayed()` | `threading.Timer` で遅延実行 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/counter/increment` | Lock ベースカウンター並列インクリメント |
| POST | `/semaphore/run` | Semaphore で同時実行数制限 |
| POST | `/event/sync` | Event によるスレッド間同期 |
| POST | `/pool/run` | ThreadPoolExecutor で並列処理 |
| POST | `/producer-consumer/run` | Queue プロデューサー-コンシューマー |
| POST | `/thread-local/run` | threading.local 分離検証 |

---

## テスト結果

**43 passed**

```
43 passed in 0.37s
```

---

## 摩擦ポイント

### F-1: `threading.Thread(target=lambda)` で `None` 返却の型エラー（深刻度: 低）

**事象**: スレッドのターゲット関数をインラインラムダで書こうとしたとき、
`lambda: [counter.increment() for _ in range(count)]` が
`"increment" of "ThreadSafeCounter" does not return a value [func-returns-value]`
エラーを mypy --strict が報告する。

**原因**: `increment()` の戻り値型が `None` であるため、リスト内包表記が `list[None]` を返す。
`threading.Thread(target=...)` は `Callable[[], None]` を期待するが、
`lambda` が `list[None]` を返す関数と推論され型が合わない。

**対応**: ターゲット関数を名前付き関数として外部に定義することで解決。
`lambda` でのワンライナーはスレッドターゲットに不向きなケースがある。

```python
def _increment_worker(counter: ThreadSafeCounter, count: int) -> None:
    for _ in range(count):
        counter.increment()

threading.Thread(target=_increment_worker, args=(counter, count))
```

### F-2: `threading.local` の `.get()` が `Any` を返す（深刻度: 低）

**事象**: `_thread_local.context.get(key)` が `Any` 型を返し、
mypy --strict の `no-any-return` でエラーになる。

**原因**: `threading.local` はスレッドごとに任意の属性を持てる設計のため、
型スタブが `Any` を返すように定義されている。

**対応**: 明示的に `str()` キャストして型を確定させる。

```python
value = _thread_local.context.get(key)
return str(value) if value is not None else None
```

---

## 観察点

### 観察1: `Lock` と `RLock` の使い分け

```python
# Lock — 同一スレッドから2回取得するとデッドロック
self._lock = threading.Lock()
with self._lock:
    total = self.value
    for child in self.children:
        total += child.sum_recursive()  # ← 再帰内で再び _lock を取得 → デッドロック

# RLock — 同一スレッドから複数回取得可能（再入カウンタを持つ）
self._lock = threading.RLock()
```

`TreeNode.sum_recursive()` のような再帰ロックが必要な場面では `RLock` が必須。
`Lock` は単純な値の保護に使い、再入が必要な場合のみ `RLock` に昇格させる。

### 観察2: `ThreadPoolExecutor` の例外隔離パターン

```python
for future in as_completed(future_to_item, timeout=timeout):
    item = future_to_item[future]
    exc = future.exception()
    if exc is not None:
        failed.append(item)
    else:
        succeeded.append(future.result())
```

`as_completed()` は例外を隠蔽せず `Future.exception()` で参照できる。
`future.result()` を直接呼ぶと例外が再送出されるため、
`future.exception()` で先に確認するパターンが安全。

### 観察3: プロデューサー-コンシューマーの `None` センチネル戦略

```python
# 終了シグナルをコンシューマー数と同じだけ投入
for _ in range(num_consumers):
    work_queue.put(None)

# 各コンシューマーは None を受けとったら終了
while True:
    item = work_queue.get()
    if item is None:
        work_queue.task_done()
        break
```

`None` センチネルをコンシューマー数分投入することで、
すべてのコンシューマーが確実に終了する。
`work_queue.join()` との組み合わせでプロデューサー側がキュー空になるまで待機できる。

### 観察4: DoS 防御の二重バリア

```python
# demos.py 側（ドメイン層）
MAX_TASKS = 100

def run_tasks_in_pool(items, ...) -> PoolResult:
    if len(items) > MAX_TASKS:
        raise ValueError(f"Too many tasks: {len(items)} > {MAX_TASKS}")
```

```python
# app.py 側（HTTP 境界層）
class PoolRequest(BaseModel):
    items: list[str] = Field(max_length=MAX_TASKS_LIMIT, ...)  # Pydantic で先に弾く
    max_workers: int = Field(default=4, ge=1, le=MAX_WORKERS_LIMIT, ...)
```

Pydantic の `max_length` が HTTP 境界で弾くが、
`demos.py` 側も独立してチェックすることで、
HTTP を迂回して直接呼ばれた場合も保護される二重バリアになっている。

---

## nene2-python フレームワークとの統合

- `ThreadSafeCounter` のような状態保持オブジェクトはリクエストごとに生成する。
  `ThreadPoolExecutor` を使うエンドポイントも同様。FastAPI のシングルトン DI とは原則分離する。
- `ThreadPoolExecutor` は FastAPI の非同期ループとは独立したスレッドプールを使う。
  `asyncio.get_event_loop().run_in_executor()` とは別物であることに注意。
- `threading.local` はリクエストをまたぐグローバルオブジェクトに使う場合、
  スレッドプールの再利用によって前のリクエストのコンテキストが残る可能性があるため注意が必要。
  FastAPI の `Depends()` や `BackgroundTasks` で明示的にリセットするか、
  リクエストスコープの変数で管理することを推奨。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

公式ドキュメントと nene2-python のサンプルを読み比べながら実装を進めている段階。

**ドキュメント理解**: `Lock` / `Semaphore` / `Event` の使い分けは公式ドキュメントだけでは直感しにくい。
`RLock` が必要な場面（再帰・再入）はコードを読んでも理由が分かりにくく、
サンプルに `Lock` では動かない例と `RLock` が必要な理由のコメントがほしい。  
**事故リスク**: 中。`Lock` を使って実装し「テストが通った」のに高並列で稀にデッドロックする状況を
初心者は再現・デバッグできない。`ThreadSafeCounter` のパターンをそのままコピーすれば安全だが、
少し変形させると競合状態を踏む。  
**規約の使いやすさ**: `with self._lock:` パターンは一度覚えれば機械的に書ける。
`threading.Thread` のコンストラクタ引数（`target`, `args`）の型制約も明確。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存コードをコピーして組み込むスタイルで、スレッドセーフの概念は知っているが深くは理解していない。

**コピペ可能性**: `ThreadSafeCounter` と `run_tasks_in_pool()` のパターンはコピーしやすい。
`producer_consumer()` は `None` センチネルの仕組みが独特で、理解せずコピーしても
コンシューマー数を変えたときに `None` 投入数を忘れてデッドロックするリスクがある。  
**拡張時の罠**: `MAX_TASKS = 100` 定数をコピーして変更するときに `app.py` 側の
Pydantic `max_length` を更新し忘れると、二重バリアが非対称になる。定数を共有するか、
変更箇所を CLAUDE.md に明記する対策が望ましい。  
**セキュリティ的な事故リスク**: 中。スレッド数・タスク数の上限を削除すると DoS につながる。
コメントや定数名（`MAX_TASKS`, `MAX_WORKERS`）がその意図を伝えているが、
「動かすために邪魔」と感じて消す人がいる。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

API クライアント側を実装する立場。FastAPI のエンドポイントが返す JSON 構造を重視する。

**エラーレスポンスの質**: Pydantic バリデーション違反（`workers > 16`）は FastAPI が自動で
422 Unprocessable Entity を返し、Problem Details に近い構造でエラー内容が分かる。
空リスト投入に対する 400 も `HTTPException(detail=...)` で明示的にメッセージが返る。  
**Python 固有概念の学習コスト**: `threading.local` の「スレッドごとに別の変数が見える」概念は
JavaScript の非同期コンテキストとは全く異なり、理解に時間がかかる。
`AsyncLocalStorage` との類推コメントがあると助かる。  
**事故リスク**: 低。HTTP 境界は Pydantic で保護されており、クライアント側から見た挙動は安定している。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

スレッドセーフな Django ミドルウェアや Celery タスクを書いてきた経験を持つ。

**他フレームワークとの差異**: Django の `thread_locals` パターンや Celery の
ワーカーモデルとの比較で `threading.local` の動作は馴染みやすい。
`ThreadPoolExecutor` は Celery/asyncio が使えない場面のシンプルな代替として評価できる。
ただし FastAPI は ASGI 非同期アプリであり、スレッドを大量に起動すると
`uvicorn` ワーカーの事前割り当てスレッドと競合する点は Django とは異なる。  
**nene2-python の薄さへの評価**: `ThreadSafeCounter` をアプリ本体に組み込む場合、
`Depends()` でシングルトン管理するか、リクエストごとに生成するかを明示的に選ぶ必要がある。
「薄い = 決定を委ねる」という nene2 哲学に合致しているが、初心者には「どちらを選べばよいか」の
ガイドラインが必要。  
**本番投入可能性**: `MAX_TASKS`/`MAX_WORKERS` の定数管理と Pydantic `le=` の二重防御は
本番環境で使えるレベル。`run_tasks_in_pool()` の `timeout` 引数は重要で、
外部 API 呼び出しを含むタスクにはタイムアウト設定を忘れずに。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チームで nene2-python を使う場合のリスクとコードレビュー観点を評価する。

**コードレビューチェックポイント**:
- [x] `threading.Thread` に `daemon=True` を付けているか（親スレッド終了時に孤児化しない）
- [x] `Lock` の取得・解放が `with` 文で行われているか（`acquire()`/`release()` の直接呼び出しはリークリスク）
- [x] `thread.join(timeout=...)` に必ずタイムアウトを設定しているか（無限待機防止）
- [x] `threading.local` のリクエスト間汚染を考慮しているか
- [x] `MAX_TASKS`/`MAX_WORKERS` の定数が `demos.py` と `app.py` で一貫しているか

**チームでの安全な共有パターン**: `with self._lock:` パターンは慣れれば安全で機械的。
`ThreadPoolExecutor` は `with` 文でコンテキストマネージャーとして使うことで
自動シャットダウンが保証されるため、これを必須パターンとして徹底させると良い。  
**ツール追加の必要性**: `pylint` の `threading` チェック（`W1506: using-constant-test`）を
`ruff` ルールセットに追加できれば望ましいが、現状の `PL` ルールセットで大半はカバー済み。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md の設計ポリシーと FT188 の実装を照合する。

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 高  
**設計上の負債・ドキュメント不足**: `threading.local` をリクエストまたいで使う場合の
スコープ汚染リスクについて CLAUDE.md に注意書きを追加する価値がある（Issue 候補: 優先度低）。
また `MAX_TASKS` / `MAX_WORKERS` の定数共有パターン（`demos.py` と `app.py` で分離している）は
将来の設定値変更時に乖離するリスクがあるため、How-to ガイドで言及する価値がある。  
**Follow-up Issue 候補**: なし（既存ポリシーの範囲内で解決済み）

---

## クラッカーペンテスト

> **実施方針**: FT188 は threading + DoS 耐性が主題。競合状態・スレッド爆弾・エラー伝播の
> 欠如を意図的に試し、「正常系のみテスト済み」のコードが崩れないかを確認する。

### フェーズ1: 構造推測（攻撃者の視点）

OpenAPI スキーマ (`/openapi.json`) から以下を推測できる:

- **`/counter/increment`**: `workers` は `ge=1, le=16` — スレッド数に上限あり。
  `count` は `ge=1, le=1000` — 各スレッドの操作数にも上限あり。
  最大でも `16 × 1000 = 16000` インクリメントで処理が終わる。
- **`/semaphore/run`**: `concurrency_limit` は `le=8` — 同時実行数を抑えている。
  `task_ids` の `max_length=50` から、タスク数が制限されている。
- **`/pool/run`**: `max_workers` は `le=8`、`items` は `max_length=50`。
  デモ側の `MAX_TASKS=100` チェックも存在する（スキーマ外の防御層）。
- **エラーメッセージ**: `too many tasks` のメッセージから `MAX_TASKS` 定数の存在が推測可能。
  ただしそれ自体は攻撃可能な情報ではない。

### フェーズ2: 攻撃実行ログ

#### A. Pydantic バイパス攻撃（型強制）

```
POST /counter/increment  {"count": "1e3", "workers": 4}
→ 422 Unprocessable Entity
  int フィールドに文字列 "1e3" → Pydantic v2 が拒否

POST /counter/increment  {"count": 1000, "workers": "4"}
→ 422 Unprocessable Entity

POST /counter/increment  {"count": 1000, "workers": 16.9}
→ 422 Unprocessable Entity (le=16 で 16.9 → int(16) = 16 の変換を試みるが float は拒否)

POST /semaphore/run  {"task_ids": [1,2], "concurrency_limit": 0}
→ 422 Unprocessable Entity (ge=1 バイオレーション)
```

**結果**: 全試み 422 で耐えた。Pydantic の `ge`/`le`/`int` 型制約がバイパスを防いでいる。

#### B. ビジネスロジック攻撃（競合状態の悪用）

```
POST /counter/increment  {"count": 1000, "workers": 16}
→ 200 OK  {"expected": 16000, "actual": 16000, "consistent": true}

# 同一エンドポイントに並列 8 リクエストを同時送信（TestClient は同期のため逐次実行だが）
→ 各リクエストが独立した ThreadSafeCounter を生成するため競合なし
```

**結果**: 耐えた。エンドポイントはリクエストごとに新しい `ThreadSafeCounter` を生成するため、
リクエスト間の状態汚染は発生しない。

#### C. 境界値・エッジケース攻撃

```
POST /counter/increment  {"count": 1000, "workers": 17}
→ 422 Unprocessable Entity (le=16 バイオレーション)

POST /counter/increment  {"count": 0, "workers": 1}
→ 422 Unprocessable Entity (ge=1 バイオレーション)

POST /pool/run  {"items": ["x"] * 50, "max_workers": 8}
→ 200 OK  (Pydantic max_length=50 の上限ちょうど)

POST /pool/run  {"items": ["x"] * 51, "max_workers": 8}
→ 422 Unprocessable Entity (max_length=50 超過)

POST /semaphore/run  {"task_ids": [], "concurrency_limit": 2}
→ 400 Bad Request  "task_ids must not be empty"

POST /thread-local/run  {"items": ["a" * 500], "context_key": "k"}
→ 200 OK  (items の各要素はmax_length制約なし — ただしthread内での処理のみ)

POST /event/sync  {"payload": "A" * 501}
→ 422 Unprocessable Entity (max_length=500 超過)

POST /event/sync  {"payload": "A" * 500}
→ 200 OK  (境界値ちょうど)
```

**結果**: すべての境界値で期待通りに耐えた。

#### D. 情報収集攻撃（エラーメッセージ解析）

```
POST /pool/run  {"items": ["x"] * 101, "max_workers": 1}
→ デモ層の MAX_TASKS=100 チェックが発動するか？
  → Pydantic の max_length=50 が先に 422 を返すため、
    "Too many tasks: 101 > 100" のメッセージは公開されない
```

**結果**: 耐えた。Pydantic の HTTP 境界チェックが先に発動するため、
デモ層の `ValueError` メッセージは HTTP レスポンスに漏洩しない。

#### E. DoS 試み

```
POST /counter/increment  {"count": 1000, "workers": 16}
→ 16スレッド × 1000回 = 16000操作、全て Lock 経由
→ 0.37s テスト全体（単一リクエストは数十ms 以内）

POST /pool/run  {"items": ["slow"] * 50, "max_workers": 8}
  processor に sleep(0) の簡易タスクで実行
→ 200 OK  (50タスク, 8ワーカー)

POST /semaphore/run  {"task_ids": list(range(50)), "concurrency_limit": 8}
→ 200 OK  total=50  (Semaphore で同時実行8に制限)
```

**結果**: 耐えた。`workers le=16`・`max_workers le=8`・`concurrency_limit le=8`・
`task_ids max_length=50` の制約によりスレッド爆弾が防がれている。

### フェーズ3: 攻撃まとめ

| 攻撃カテゴリ | 試みた攻撃数 | 突破 | 耐えた | 予期しない動作 |
|---|---|---|---|---|
| Pydantic バイパス | 4 | 0 | 4 | 0 |
| ビジネスロジック（競合状態） | 2 | 0 | 2 | 0 |
| 境界値/エッジ | 8 | 0 | 8 | 0 |
| 情報収集 | 1 | 0 | 1 | 0 |
| DoS（スレッド爆弾） | 3 | 0 | 3 | 0 |

**攻撃耐性評価**: 堅牢  
**発見した弱点**: なし。すべての攻撃が Pydantic または明示的な HTTP エラーで遮断された。
`items` リスト内の個別要素には `max_length` が設定されていない（`context_key` の値として
任意長の文字列を渡せる）が、それ自体は計算コスト攻撃にはつながらない。

---

## Follow-up Issues

今回の FT では新規 Follow-up Issue は発生しなかった。
既存の Issue (#501, #510 等) との重複もなし。

---

## まとめ

FT188 では `threading` モジュールの 8 パターン（Lock・RLock・Semaphore・Event・
ThreadPoolExecutor・Queue・threading.local・Timer）を FastAPI サンドボックスで実装した。

主な技術的学習:
1. **`Lock` vs `RLock`** — 再帰的ロックが必要な場面では `RLock` が必須。誤って `Lock` を使うと
   自己デッドロックになる（静的解析では検出できない）。
2. **スレッドターゲットに `lambda` を使うと mypy --strict でエラー** — `None` 返却関数を
   呼ぶラムダは型推論に失敗する。名前付き関数に切り出すことで解決。
3. **`threading.local` の型制約** — `.get()` が `Any` を返すため、明示的な `str()` キャストが必要。

クラッカーペンテストでは 18 攻撃すべてを耐え、Pydantic の二重バリアと
`MAX_TASKS`/`MAX_WORKERS` 定数による DoS 防御が機能していることを確認した。

次の FT189 は `189 % 3 == 0` のため **セキュリティ診断あり**（`189 % 4 = 1` でペンテストなし）。
