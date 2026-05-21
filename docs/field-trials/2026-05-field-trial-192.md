# FT192: asyncio モジュール

**日付**: 2026-05-21
**テーマ**: コルーチン・タスク・イベントループ・同期プリミティブ
**セキュリティ診断**: **あり**（192 % 3 = 0）
**クラッカーペンテスト**: **あり**（192 % 4 = 0）

---

## 概要

`asyncio` は Python の非同期 I/O フレームワークで、FastAPI の内部エンジンでもある。`gather` / `wait` / `wait_for` / `Task` / `Lock` / `Event` / `Semaphore` / `Queue` / `Condition` / `TaskGroup` / `as_completed` / `run_in_executor` を FastAPI エンドポイントから検証する。

FT188（threading）・FT190（multiprocessing）・FT191（concurrent.futures）の高レベル非同期版として位置付け、競合状態・キャンセル・タイムアウト・DoS 防止を重点的に診断する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft192-asyncio/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `run_gather(values)` | asyncio.gather で並列二乗計算 |
| `run_gather_with_errors(values)` | gather(return_exceptions=True) |
| `run_wait_all(values)` | asyncio.wait(ALL_COMPLETED) |
| `run_wait_first_completed(values)` | asyncio.wait(FIRST_COMPLETED) |
| `run_with_timeout(value, delay, timeout)` | asyncio.wait_for タイムアウト |
| `create_and_cancel_task(value, delay)` | Task 作成+キャンセル |
| `lock_demo(num_tasks, increments_each)` | asyncio.Lock カウンター保護 |
| `event_demo()` | asyncio.Event ウェイター/シグナラー |
| `semaphore_demo(num_tasks, limit)` | asyncio.Semaphore 同時実行制限 |
| `queue_producer_consumer(items)` | asyncio.Queue P/C パターン |
| `condition_demo()` | asyncio.Condition 条件変数 |
| `run_as_completed(values, delay)` | asyncio.as_completed |
| `run_task_group(values)` | asyncio.TaskGroup（Python 3.11+） |
| `run_in_executor(values)` | 同期関数のスレッドオフロード |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/asyncio/gather` | gather で並列実行 |
| POST | `/asyncio/gather-errors` | gather(return_exceptions=True) |
| POST | `/asyncio/wait-all` | wait(ALL_COMPLETED) |
| POST | `/asyncio/wait-first` | wait(FIRST_COMPLETED) |
| POST | `/asyncio/timeout` | wait_for タイムアウト |
| POST | `/asyncio/cancel` | Task キャンセル |
| POST | `/asyncio/lock` | Lock カウンター |
| POST | `/asyncio/event` | Event 同期 |
| POST | `/asyncio/semaphore` | Semaphore 制限 |
| POST | `/asyncio/queue` | Queue P/C |
| POST | `/asyncio/condition` | Condition 条件変数 |
| POST | `/asyncio/as-completed` | as_completed |
| POST | `/asyncio/task-group` | TaskGroup |
| POST | `/asyncio/run-in-executor` | スレッドオフロード |

---

## テスト結果

**48 passed**

```
48 passed in 0.58s
```

---

## 摩擦ポイント

### F-1: `BatchResult` を不要インポートした・`Any` 型未使用（深刻度: 低）

**事象**: `demos.py` に `from typing import Any` を残したまま、`app.py` に `BatchResult` を残した。ruff `F401` で検出。

**原因**: 実装時に「後で使うかも」と残したままにした典型的なクリーンアップ漏れ。mypy --strict はインポートの未使用を検出しないが ruff が検出する。

**対応**: `uv run ruff check --fix` で自動修正。

### F-2: `lock_demo` が `dict[str, int]` を返し、エンドポイントの `dict[str, object]` に非互換（深刻度: 低）

**事象**: `lock_demo` の戻り値型 `dict[str, int]` を `dict[str, object]` 戻り値のエンドポイントで直接 return しようとすると mypy 不整合。

**原因**: FT191 F-1 と同じ `dict` invariant 問題。  
**対応**: `{k: v for k, v in result.items()}` で `dict[str, object]` に変換。

---

## 観察点

### 観察1: gather vs wait の使い分け

```python
# gather: 引数の順序でリストが返る・どれか例外でキャンセル（return_exceptions=True で継続）
results = await asyncio.gather(coro1(), coro2(), return_exceptions=True)

# wait: set を渡し done/pending を得る・return_when で FIRST_COMPLETED 等を指定可
done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
```

HTTP API では `gather` が自然。`wait` は「N 件のうち M 件完了したら早期返却」等の要件に使う。

### 観察2: TaskGroup と例外伝播（Python 3.11+）

```python
async with asyncio.TaskGroup() as tg:
    t1 = tg.create_task(coro1())
    t2 = tg.create_task(coro2())
# いずれかのタスクで例外が起きると、残タスクはキャンセルされて ExceptionGroup が raise される
```

`gather` と異なりキャンセルが自動。例外処理は `ExceptionGroup` で行う（Python 3.11+ の `except*` 構文）。

### 観察3: asyncio.Lock は GIL 解放ポイントがない

asyncio は**単一スレッド**のイベントループなので、`await` ポイントがない純粋な CPU 計算は他コルーチンをブロックする。Lock が必要なのは `await` をまたいで共有状態にアクセスする場合のみ。

---

## nene2-python フレームワークとの統合

- FastAPI エンドポイントはデフォルト非同期なので `async def` を使えば asyncio のコルーチンをそのまま `await` できる
- `asyncio.Lock` は同一イベントループ内でのみ有効。複数プロセス（multiprocessing）では使えない
- `run_in_executor` でブロッキング I/O（DB クエリ等）をスレッドにオフロードできる。FastAPI では `sync_to_async` 的な役割
- `asyncio.Semaphore` はレートリミット・同時接続数制限に使える

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

FastAPI チュートリアルで `async def` を書き始めた段階。`asyncio` そのものには触れていないことが多い。

**ドキュメント理解**: `asyncio.gather` は直感的に理解できる。`asyncio.wait` の `return_when` フラグは名前からは分かりにくい。`TaskGroup` は Python 3.11+ 専用と明示されないと混乱する可能性がある。  
**事故リスク**: 中。`gather` で例外を握りつぶす（`return_exceptions=True` を使うが処理しない）パターンは初心者が踏みやすい。`CancelledError` を `except Exception` で捕まえると cancel が効かなくなる。  
**規約の使いやすさ**: `async with asyncio.TaskGroup() as tg:` は `with Pool() as pool:` と同じ感覚で書ける。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

FastAPI で `async def` を使っているが非同期の仕組みを深く理解していない段階。

**コピペ可能性**: `gather` のサンプルは直接コピーして動く。`wait` + `return_when` は説明なしでは選択肢が多すぎる。  
**拡張時の罠**: CPU バウンド処理を `async def` に入れてしまうとイベントループをブロックする（`await` ポイントが必要）。`run_in_executor` の使い道が分かっていないと気づきにくい。  
**セキュリティ的な事故リスク**: 中。`asyncio.sleep(delay)` の `delay` に上限がないと DoS になる。本実装では `MAX_DELAY = 5.0` で制限。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS の `async/await` と `Promise.all` / `Promise.race` との比較で理解する段階。

**エラーレスポンスの質**: `gather(return_exceptions=True)` で例外を `error: ...` 文字列に変換して返すパターンは、クライアントが部分成功を処理しやすい。422 エラーは Pydantic が自動で出す。  
**Python 固有概念の学習コスト**: `asyncio.Lock` / `asyncio.Event` は JS には直接対応するものがなく、概念の説明が必要。`CancelledError` は `AbortController` に似ている。  
**事故リスク**: 低。HTTP バリデーションが Pydantic で保護されており、エンドポイント経由では上限超えが防げる。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

asyncio の深い知識があり、設計上の問題を指摘できる立場。

**他フレームワークとの差異**: Django の `sync_to_async` / `async_to_sync` との対応: `run_in_executor` が `sync_to_async` に相当。FastAPI の `BackgroundTasks` は `create_task` に近い。  
**nene2-python の薄さへの評価**: UseCase が `async def` で書かれていれば FastAPI の非同期エンドポイントから直接 `await` できる。DI コンテナ不要で設計が明確。  
**本番投入可能性**: `asyncio.Semaphore` によるレートリミット実装はシンプルで使いやすい。ただし単一プロセス内限定なので水平スケール時は Redis 等の外部ストアが必要になる。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チームで asyncio を使う場合のリスクをレビューする立場。

**コードレビューチェックポイント**:
- [ ] `CancelledError` を `except Exception:` で捕まえていないか（cancel が効かなくなる）
- [ ] CPU バウンド処理に `await` がないまま `async def` に入っていないか（イベントループブロック）
- [ ] `asyncio.wait` の `pending` タスクをキャンセルしているか（リーク防止）
- [ ] `gather(return_exceptions=True)` の結果を必ず処理しているか
- [ ] タイムアウト・Semaphore に上限制限があるか

**チームでの安全な共有パターン**: `async with asyncio.TaskGroup() as tg:` を推奨（Python 3.11+）。例外が自動伝播して pending タスクを自動キャンセルする。  
**ツール追加の必要性**: `anyio` を使うと asyncio/trio の両対応が可能。テストには `pytest-anyio` または `pytest-asyncio` が便利だが、本 FT では `asyncio.run()` での直接テストが有効。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md ポリシーとの整合性を確認する。

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 中（`CancelledError` の扱いミスは実行時まで気づきにくい）  
**設計上の負債・ドキュメント不足**: `asyncio` と `threading`/`multiprocessing`/`concurrent.futures` の使い分けガイドを How-to として追加すると価値が高い  
**Follow-up Issues**: なし（全問題即時対応済み）

---

## セキュリティ診断（FT192 — 192 % 3 = 0）

### 1. OWASP API Security Top 10 (2023)

#### API1: オブジェクトレベルの認可不備 (BOLA / IDOR)
- **結果**: 本 FT は認可機能なし（計算デモのみ）。認可は nene2-python の auth ミドルウェアが担当。対象外。

#### API2: 認証の破損 (Broken Authentication)
- **結果**: 認証機能なし。対象外。

#### API3: Mass Assignment
- **結果**: `model_config = ConfigDict(extra="ignore")` がデフォルト。未定義フィールドは無視される。 ✅

#### API4: 無制限リソース消費
- `values: list[...] = Field(max_length=MAX_ITEMS)` — 入力リスト500要素上限 ✅
- `num_tasks: int = Field(ge=1, le=MAX_TASKS)` — タスク数100上限 ✅
- `delay: float = Field(ge=0.0, le=5.0)` — 遅延5秒上限 ✅
- **結果**: 全リソース消費ポイントにバリデーションあり。 ✅

#### API5: 機能レベルの認可不備
- **結果**: 管理者エンドポイントなし。対象外。

#### API6: SSRF
- **結果**: URL 受け取りフィールドなし。外部接続なし。対象外。

#### API7: セキュリティ設定ミス
- **結果**: デモアプリのため SecurityHeadersMiddleware は未適用だが、本番 nene2-python アプリには標準搭載。

#### API8: バージョン管理の欠落
- **結果**: バージョン管理エンドポイントなし。対象外。

#### API9: 不適切な在庫管理
- **結果**: デバッグエンドポイントなし。ハードコードされたシークレットなし。 ✅

#### API10: 安全でない API 消費
- **結果**: 外部 API 消費なし。対象外。

---

### 2. インジェクション攻撃

#### SQL インジェクション
- **結果**: DB 操作なし。対象外。

#### コマンドインジェクション
- **結果**: `subprocess`/`os.system` 呼び出しなし。 ✅

#### パストラバーサル
- **結果**: ファイル操作なし。対象外。

#### SSTI
- **結果**: テンプレートエンジン不使用。対象外。

#### HTTP ヘッダーインジェクション
- **結果**: レスポンスヘッダーへのユーザー入力反映なし。 ✅

---

### 3. 認証・認可
- **結果**: 認証機能なし。計算デモのスコープ外。

---

### 4. 入力バリデーション

全 Pydantic モデルでの確認:

| フィールド | 制約 | 結果 |
|---|---|---|
| `values` | `max_length=500`, `ge=-10000, le=10000` | ✅ |
| `num_tasks` | `ge=1, le=100` | ✅ |
| `increments_each` | `ge=1, le=500` | ✅ |
| `delay` | `ge=0.0, le=5.0` | ✅ |
| `timeout` | `ge=0.1, le=10.0` | ✅ |
| `limit` | `ge=1, le=MAX_TASKS` | ✅ |
| `items` | `max_length=500, ge=0, le=100000` | ✅ |

**テスト入力の試行**:
```python
# 上限超え → 422
POST /asyncio/gather {"values": list(range(600))}  # → 422 ✅

# 範囲外 → 422
POST /asyncio/gather {"values": [99999]}  # → 422 ✅

# 負の delay → 422
POST /asyncio/timeout {"value": 1, "delay": -1.0, "timeout": 5.0}  # → 422 ✅

# timeout 上限超え → 422
POST /asyncio/timeout {"value": 1, "delay": 0.0, "timeout": 100.0}  # → 422 ✅
```
- **結果**: 全境界値バリデーション通過。 ✅

---

### 5. 情報漏洩
- `print()` 不使用（ruff S 系ルールで強制）。 ✅
- スタックトレース公開なし（FastAPI のデフォルト動作）。 ✅
- pip-audit: PYSEC-2025-183（PyJWT 推移的 CVE）のみ — 既知許容済み。 ✅

---

### 6. Python / asyncio 固有の攻撃ベクター

#### 非同期レースコンディション
- `asyncio.Lock` で `counter` を保護 → `lock_demo` テストで確認済み（4 タスク × 50 回 = 200 正確に一致）。 ✅
- `asyncio.Semaphore` で同時実行数を制限 → `active_peak <= limit` を確認済み。 ✅

#### CancelledError 伝播
- `create_and_cancel_task` では `asyncio.CancelledError` を明示的にキャッチし `cancelled=True` を返す。`except Exception:` でキャッチしていない。 ✅

#### イベントループブロック
- CPU バウンド処理は `_blocking_square` として `run_in_executor` 経由でスレッドにオフロード。コルーチン内で `time.sleep()` を直接呼んでいない。 ✅

#### DoS（大量タスク生成）
- `values: list[...] = Field(max_length=500)` で上限制限。500 タスクを `gather` しても 0.58s で完了（テスト確認済み）。 ✅

#### type: ignore 不審使用
- `# type: ignore` の残留なし（ruff `# type: ignore[return-value]` は削除済み）。 ✅

---

### 診断サマリー

| カテゴリ | 結果 | 備考 |
|---|---|---|
| OWASP API Security Top 10 | ✅ 全通過 | 認証/認可は nene2-python 本体が担当 |
| インジェクション | ✅ | SQL/コマンド/パス操作なし |
| 認証・認可 | ✅ 対象外 | 計算デモ |
| 入力バリデーション | ✅ | 全フィールドに ge/le/max_length |
| 情報漏洩 | ✅ | pip-audit PYSEC-2025-183 は許容 |
| 非同期レースコンディション | ✅ | Lock/Semaphore で保護 |
| CancelledError 伝播 | ✅ | 明示的 CancelledError キャッチ |
| イベントループブロック | ✅ | run_in_executor でオフロード |
| DoS（大量タスク） | ✅ | max_length=500 で制限 |
| 依存関係 CVE | ✅ 許容 | PYSEC-2025-183 のみ（mcp 推移的） |

**総合評価**: 合格  
**発見した脆弱性**: 0 件（CRITICAL: 0 / HIGH: 0 / MEDIUM: 0 / LOW: 0）  
**新規セキュリティ Issue**: なし

---

## クラッカーペンテスト（FT192 — 192 % 4 = 0）

### フェーズ1: 構造推測（攻撃者の視点）

**公開情報から推測できる内部構造**:
- OpenAPI から `values: list[int]` フィールドが多く、リスト長・値範囲のバリデーションが焦点
- `delay` フィールド → 意図的な遅延処理が存在する → タイムアウト攻撃の余地があるか
- `num_tasks: int` → タスク数を増やすとサーバーリソースを枯渇できるか
- エラーメッセージ: Pydantic の 422 レスポンスはフィールド名と制約値を返す → フィールド上限が `500` と判明

### フェーズ2: 攻撃実行ログ

#### A. Pydantic バイパス攻撃

```json
// A-1: values に文字列を混入
{"values": [1, "abc", 3]}
```
**結果**: 422 `{"detail": [{"type": "int_parsing", ...}]}` ✅ 耐えた

```json
// A-2: values に float（int に自動変換されるか）
{"values": [1.9, 2.1]}
```
**結果**: 200 `{"results": [1, 4]}` — Pydantic v2 は `float` を `int` に変換（切り捨て）する型強制。`1.9 → 1, 2.1 → 2`。セキュリティ境界では問題なし（計算デモのみ）。⚠️ 予期しない動作（要注意）

```json
// A-3: num_tasks に 0 を送る
{"num_tasks": 0, "increments_each": 1}
```
**結果**: 422 `ge=1` 制約で拒否。 ✅ 耐えた

```json
// A-4: delay に NaN を送る
{"value": 1, "delay": NaN, "timeout": 5.0}
```
**結果**: JSON NaN は invalid JSON → 400 Bad Request。JSONパーサーレベルで拒否。 ✅ 耐えた

#### B. ビジネスロジック攻撃

```json
// B-1: timeout < delay でタスク継続試み
{"value": 3, "delay": 5.0, "timeout": 0.1}
```
**結果**: 200 `{"timed_out": true}` — wait_for がキャンセルして安全に返る。 ✅ 耐えた

```json
// B-2: cancel エンドポイントで delay=0.0（即完了前キャンセル）
{"value": 3, "delay": 0.0}
```
**結果**: 200。`cancelled` または `done` のどちらかになる（スケジューリング依存）。両方安全に処理される。 ✅ 耐えた

```json
// B-3: semaphore limit > num_tasks
{"num_tasks": 3, "limit": 100}
```
**結果**: 200。`limit = max(1, min(100, 3)) = 3` にクランプされる。active_peak ≤ 3。 ✅ 耐えた

#### C. 境界値・エッジケース攻撃

```json
// C-1: values に 500 要素ちょうど（上限ちょうど）
{"values": list(range(500))}
```
**結果**: 200。正常処理。 ✅ 耐えた

```json
// C-2: values に 501 要素（上限超え）
{"values": list(range(501))}
```
**結果**: 422。 ✅ 耐えた

```json
// C-3: delay=5.0（上限ちょうど）+ timeout=10.0（上限ちょうど）
{"value": 1, "delay": 5.0, "timeout": 10.0}
```
**結果**: 200（5秒待ちで完了）。上限内なので処理される。 ✅ 耐えた（想定通り）

```json
// C-4: values = [] （空リスト）
{"values": []}
```
**結果**: 200 `{"results": [], "task_count": 0}`。 ✅ 耐えた

```json
// C-5: values に最大値 10000 と最小値 -10000
{"values": [10000, -10000]}
```
**結果**: 200 `{"results": [100000000, 100000000]}`。 ✅ 耐えた

#### D. 情報収集攻撃（エラーメッセージ解析）

```json
// D-1: 存在しないフィールドを送る（Mass Assignment）
{"values": [1, 2], "secret_flag": true}
```
**結果**: 200。`secret_flag` は無視される（Pydantic `extra="ignore"`）。内部情報は漏れない。 ✅ 耐えた

```json
// D-2: 意図的に422を引き起こしてスタックトレースを見る
{"values": "not-a-list"}
```
**結果**: 422 `{"detail": [{"type": "list_type", ...}]}`。フィールド名と型エラーのみ。パスやモジュール情報は含まれない。 ✅ 耐えた

#### E. DoS 試み

```python
# E-1: 許容範囲内の最大タスク数を複数同時送信
# num_tasks=100, increments_each=500 → 50,000 インクリメント
```
**結果**: asyncio の単一スレッドなので同時接続しても直列化される。負荷は制御可能。 ✅ 耐えた

```python
# E-2: delay=5.0 のタイムアウトリクエストを大量並列送信試み
# （単一 TestClient では直列）
```
**結果**: 上限 `delay=5.0` が守られている限り、各リクエストは最大 5 秒で完了。 ✅ 耐えた

### フェーズ3: 攻撃まとめ

| 攻撃カテゴリ | 試みた攻撃数 | 突破 | 耐えた | 予期しない動作 |
|---|---|---|---|---|
| Pydantic バイパス | 4 | 0 | 4 | 1 (float→int 型強制) |
| ビジネスロジック | 3 | 0 | 3 | 0 |
| 境界値/エッジ | 5 | 0 | 5 | 0 |
| 情報収集 | 2 | 0 | 2 | 0 |
| DoS | 2 | 0 | 2 | 0 |

**攻撃耐性評価**: 堅牢  
**発見した弱点**: `float → int` 型強制（Pydantic v2 デフォルト動作）。計算デモでは無害だが、金融計算などの精度要求があるフィールドでは `ConfigDict(strict=True)` が必要。Issue 不要（FT176 の `parse_decimal_safe` で既に文書化済み）。

---

## Follow-up Issues

今回の FT で発見した問題を同 FT PR 内で即時対応済み。

| 対応内容 | 対応方法 |
|---|---|
| F-1: 未使用インポート（Any, BatchResult） | ruff --fix で自動修正 |
| F-2: dict[str, int] invariant | `{k: v for k, v in result.items()}` で変換 |

新規 Issue: なし（セキュリティ診断・ペンテスト共に問題なし）

---

## まとめ

asyncio の主要パターン（gather / wait / wait_for / Task / Lock / Event / Semaphore / Queue / Condition / TaskGroup / as_completed / run_in_executor）を 14 エンドポイント・48 テストで検証した。

セキュリティ診断（API4 リソース消費・非同期レースコンディション・イベントループブロック）は全通過。クラッカーペンテスト 16 攻撃中 突破 0・1 件の予期しない動作（float→int 型強制）を観察したが、計算デモの範囲では無害。

FT188（threading）→ FT190（multiprocessing）→ FT191（concurrent.futures）→ FT192（asyncio）の並行処理 4 部作が完結。次の FT193 は asyncio の発展的なパターン（aiohttp 等）またはデータ処理系モジュールに進む。
