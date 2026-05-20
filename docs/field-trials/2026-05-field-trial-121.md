# Field Trial 121: asyncio.gather + asyncio.TaskGroup 並列処理

## テーマ

`asyncio.gather` と Python 3.11+ の `asyncio.TaskGroup` を使って、
複数の非同期処理を並行実行して応答時間を短縮するパターンを検証する。
FastAPI の `async def` エンドポイントとの統合、実際の並列性をタイム計測で確認する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft121-async-gather/` に以下を実装:

- `get_product_page_gather()` — `asyncio.gather` でユーザー情報・在庫を並行取得
- `get_product_page_taskgroup()` — `asyncio.TaskGroup` で同様の並行取得
- `get_multiple_products()` — `TaskGroup` で可変長の並行タスク
- `@pytest.mark.anyio` で async テストを実施（並列性をタイム計測で検証）
- 10 テスト通過

## テスト結果

全 10 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `asyncio.gather` は Python 3.11 以前からの標準並行パターン

```python
user, inventory = await asyncio.gather(
    fetch_user_info(user_id),
    fetch_inventory(product_id),
)
# 2つのコルーチンが並行実行される
```

全コルーチンが完了するまで待機する。いずれかが例外を raise すると残りはキャンセルされない（`return_exceptions=True` で制御可能）。

### O2: `asyncio.TaskGroup`（Python 3.11+）は例外安全な並行実行

```python
async with asyncio.TaskGroup() as tg:
    user_task = tg.create_task(fetch_user_info(user_id))
    inventory_task = tg.create_task(fetch_inventory(product_id))

user = user_task.result()  # with ブロック終了後に結果を取得
```

`TaskGroup` はいずれかのタスクが例外を raise すると他のタスクをキャンセルし、
全例外を `ExceptionGroup` としてまとめる。より安全な並行実行パターン。

### O3: pytest で async テストには `@pytest.mark.anyio` を使う

```python
@pytest.mark.anyio
async def test_gather_is_parallel() -> None:
    start = time.perf_counter()
    await get_product_page_gather(1, 1)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.12  # 並行なら ~0.05s、逐次なら ~0.15s
```

`anyio` 経由で pytest に async テストを統合できる。`asyncio` バックエンドで実行される。

### O4: `gather` vs `TaskGroup` の使い分け

| 特性 | `asyncio.gather` | `asyncio.TaskGroup` |
|---|---|---|
| Python バージョン | 3.x | 3.11+ |
| 例外処理 | 最初の例外で停止（デフォルト） | `ExceptionGroup` にまとめる |
| 可変長タスク | `gather(*coros)` | `tg.create_task()` を繰り返す |
| 結果取得 | タプルアンパック | `task.result()` |

固定数の並行タスクなら `gather`、動的数や例外安全が重要なら `TaskGroup` が適切。

## まとめ

FT121 は摩擦ゼロ確認。FastAPI の `async def` エンドポイントと `asyncio.gather` / `TaskGroup` は
シームレスに統合できる。並行実行で応答時間を短縮できることをタイム計測で確認した。
