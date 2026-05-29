# How-to: 並行処理パターンの選び方

FT188（threading）〜 FT192（asyncio）の知見をまとめたガイド。
nene2-python では **UseCase 層は HTTP に依存しない**ため、並行処理の選択は UseCase または HTTP ハンドラー層で行う。

---

## クイック選択表

| 用途 | 推奨 | FT |
|---|---|---|
| FastAPI ハンドラー内の I/O 待ち | `async def` + `await` | FT192 |
| 同期 UseCase を非ブロッキング実行 | `AsyncUseCaseProtocol` | FT6, FT14 |
| CPU バウンドをスレッドに逃がす | `asyncio.to_thread()` または `ThreadPoolExecutor` | FT188, FT191 |
| CPU バウンドをプロセスに逃がす | `ProcessPoolExecutor` / `multiprocessing` | FT190, FT191 |
| バックグラウンドで外部コマンド | `subprocess`（`shell=False` + allowlist） | FT189 |
| 共有 in-memory キャッシュ | `TtlCache[V]`（スレッドセーフ） | FT119, FT171 |

---

## asyncio（FT192）

FastAPI ルートは `async def` が基本。複数 I/O を並列化する場合:

```python
import asyncio

async def execute(self, input_: ListNotesInput) -> ListNotesOutput:
    items_task = asyncio.create_task(self._repository.find_all_async(...))
    total_task = asyncio.create_task(self._repository.count_async())
    items, total = await asyncio.gather(items_task, total_task)
    return ListNotesOutput(items=items, total=total, ...)
```

**注意**: Pydantic v2 は `float` を `int` に切り捨て変換する。数値境界は `Field(ge=..., le=...)` で明示する。

---

## threading（FT188）

GIL 下では CPU 並列化には不向きだが、**ブロッキング I/O を async 化しないレガシー API** との橋渡しに有効。

- `threading.Lock` / `asyncio.Lock` — 共有状態の保護
- `ThreadPoolExecutor` — 同期関数のオフロード（FT191 と組み合わせ）

---

## subprocess（FT189）

**必須ルール**（CLAUDE.md / FT189 セキュリティ診断）:

1. `shell=False` のみ
2. コマンド名を allowlist で検証
3. タイムアウトと stdout サイズ上限
4. ruff S603 は allowlist 検証後に `# noqa: S603`（理由を docstring に記載）

---

## nene2 との整合

| 層 | 並行処理 |
|---|---|
| UseCase | `AsyncUseCaseProtocol` または純粋同期（InMemory テスト可能） |
| HTTP | `async def` ハンドラー、`BackgroundTasks`（[background-tasks.md](background-tasks.md)） |
| Middleware | 同期 ASGI；ブロッキング処理をミドルウェア内に置かない |
| MCP | UseCase をそのままツール化 — 並行は UseCase 内で完結 |

詳細レポート: [FT188](../../field-trials/2026-05-field-trial-188.md) · [FT189](../../field-trials/2026-05-field-trial-189.md) · [FT190](../../field-trials/2026-05-field-trial-190.md) · [FT191](../../field-trials/2026-05-field-trial-191.md) · [FT192](../../field-trials/2026-05-field-trial-192.md)
