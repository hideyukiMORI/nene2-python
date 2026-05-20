# FT76: async ハンドラー + sync SQLAlchemy のイベントループブロッキング

**日付**: 2026-05-20  
**テーマ**: FastAPI の async def ハンドラー内で同期 DB 処理を呼ぶとどうなるか  
**バージョン**: v1.8.21  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft76-async-sync-db/`

---

## 概要

FastAPI は `async def` と `def` を混在できるが、同期処理の扱いが根本的に異なる。
nene2 の DB 層（`SqlAlchemyQueryExecutor` / `SqlAlchemyTransactionManager`）は同期実装のため、
`async def` ハンドラー内から直接呼ぶとイベントループをブロックする。
このFTでは3パターンの挙動を実測し、nene2 として何を提供すべきかを検証した。

---

## テスト対象の3パターン

| パターン | 実装 | 動作 |
|---|---|---|
| A | `async def` 内で `time.sleep()` / 同期DB直呼び | **イベントループをブロック** |
| B | `async def` 内で `run_in_executor()` 経由 | スレッドプールにオフロード（安全） |
| C | `def` ハンドラー（同期） | FastAPI が自動でスレッドプールに退避（安全） |

---

## 発見した問題

### 問題1: async ハンドラー + sync DB = サイレントブロッキング

```python
# ❌ よくある間違い
@app.post("/tasks")
async def create_task(body: TaskBody) -> JSONResponse:
    result = _create_task_sync(body.title)  # time.sleep / Session(...) など
    return JSONResponse(result, status_code=201)
```

`async def` 内で `time.sleep()` や同期 `Session` を呼ぶと、実行中は asyncio のイベントループが
完全に停止する。他のリクエストはそのリクエストが完了するまで待たされる。

**特に危険なのは「少量のデータなら問題が出ない」点**。
開発中 / ステージング環境では顕在化せず、本番で同時アクセスが増えてから遅延が爆発する。

### 問題2: nene2 に async DB 層がない

```python
# v1.8.21 時点: 存在しない
from nene2.database import AsyncSqlAlchemyQueryExecutor  # ImportError
```

`SqlAlchemyQueryExecutor.fetch_all()` / `SqlAlchemyTransactionManager.begin()` は
すべて同期実装。async def ハンドラーと組み合わせるには自前で `run_in_executor` を書く必要がある。

### 問題3: run_in_executor パターンが冗長で発見しにくい

```python
# ✅ 正しいが、毎回これを書くのは辛い
@app.post("/tasks")
async def create_task(body: TaskBody) -> JSONResponse:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _create_task_sync, body.title, body.simulate_ms)
    return JSONResponse(result, status_code=201)
```

- `asyncio.get_event_loop()` は Python 3.10+ で deprecation warning を出すことがある
- `None` の意味（default executor = ThreadPoolExecutor）が自明でない
- 複数の引数を渡すには `functools.partial` か lambda が必要になりさらに冗長になる

### 問題4: `def` ハンドラーが実は最もシンプルで安全

```python
# ✅ sync def は FastAPI が自動でスレッドプールに退避する
@app.post("/tasks")
def create_task(body: TaskBody) -> JSONResponse:
    result = _create_task_sync(body.title)  # 安全
    return JSONResponse(result, status_code=201)
```

`async def` を書く必然性がないなら `def` を使うべきだが、
「FastAPI = async」というイメージから全ハンドラーを `async def` にするユーザーが多い。
nene2 のドキュメントがこれを明示していない。

---

## テスト結果（全12件パス）

```
test_sync_in_async_creates_task     PASSED  # パターンA: 機能はする（ブロッキングだが）
test_executor_creates_task          PASSED  # パターンB: executor 経由
test_sync_def_creates_task          PASSED  # パターンC: sync def
test_list_tasks                     PASSED
test_sync_def_does_not_block_event_loop  PASSED  # イベントループが自由であることを確認
test_sync_in_async_blocks_when_slow     PASSED  # 200ms スリープがそのまま待機時間になる
test_executor_avoids_blocking           PASSED
test_middlewares_work_with_all_patterns PASSED  # setup_middlewares() は全パターンで動作
test_422_on_invalid_title_length        PASSED
test_422_on_negative_simulate_ms        PASSED
test_no_async_db_layer_in_nene2         PASSED  # 非同期DB層が存在しないことを確認
test_threadpool_pattern_is_verbose      PASSED  # 冗長さのドキュメンタリーテスト
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F76-1 | nene2 に async DB 層がなく、async ハンドラーでは run_in_executor が必要 | 高 |
| F76-2 | async def + sync DB のブロッキングがサイレント（警告なし） | 高 |
| F76-3 | run_in_executor の書き方が冗長で、正しい引数渡しが分かりにくい | 中 |
| F76-4 | ドキュメントが async def vs def の使い分けを説明していない | 中 |

---

## 使用感（主観評価）

### 直感性 ★★☆☆☆

「FastAPI を使っているので全ハンドラーを async def にする」のは自然な発想。
しかし nene2 の DB 層は同期なので、これが罠になる。
`async def` で書いたコードが正常に動き、テストも全部通る — でも本番では爆発する。
「動いているから正しい」と思ってしまう構造が非常にやっかいで直感に反する。

### 実害の深刻さ ★★★★☆

本番環境で同時アクセスが増えてからはじめて顕在化する。
レスポンスが遅い → サーバーがダウン、という流れをたどる典型的なパフォーマンス地雷。
「なぜか重い」「スケールしない」という症状で現れるため、根本原因の特定も遅れやすい。

### 修正のしやすさ ★★☆☆☆

`run_in_executor` パターンを知っていれば直せるが、記述が冗長で毎回ハンドラーに書くのはつらい。
根本解決（async DB 層の実装）はSQLAlchemy async対応が必要で、工数が大きい。
`def` ハンドラーへの移行が最もシンプルだが、`async` 依存のロジックが混在していると難しい。

### 総合コメント

FastAPI + SQLAlchemy の組み合わせは最も多いユースケースの一つ。
「nene2 を使えばすぐ始められる」が「パフォーマンス問題で詰まる」という流れは
ユーザー離れを引き起こす可能性がある。
`def` vs `async def` の使い分けガイドラインと、将来的な async DB サポートが必要。

---

## 推奨アクション

1. **Issue**: `async def` ハンドラー内での `SqlAlchemy` 同期呼び出し警告をドキュメントに追加
2. **Issue**: `run_in_threadpool()` ヘルパー（または `asyncify()` パターン）の提供
3. **将来**: `AsyncSqlAlchemyQueryExecutor` の実装（SQLAlchemy 2.0 async 対応）
