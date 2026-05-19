# ADR-0010: AsyncUseCase パターン

## ステータス

承認済み (2026-05-19)

## コンテキスト

FastAPI は ASGI ベースで、ハンドラーは `async def` で定義できる。既存の UseCase はすべて同期（`def execute`）で実装されており、ブロッキング I/O（SQLAlchemy Core）を直接呼び出す。

問題:
- 外部 API 呼び出し・非同期 DB ドライバなど、真の非同期 I/O が必要なユースケースを表現できない
- 複数の I/O 操作を `asyncio.gather` で並列実行する手段がない
- 同期 UseCase と非同期 UseCase を型で区別できない

## 決定

`nene2.use_case` パッケージに 2 つの `@runtime_checkable Protocol` を定義する:

```python
@runtime_checkable
class UseCaseProtocol[I, O](Protocol):
    def execute(self, input_: I) -> O: ...

@runtime_checkable
class AsyncUseCaseProtocol[I, O](Protocol):
    async def execute(self, input_: I) -> O: ...
```

### 非同期 UseCase の実装パターン

既存の同期リポジトリを非同期コンテキストで安全に使うには `asyncio.to_thread` で I/O をスレッドプールに逃がす:

```python
class AsyncListNotesUseCase:
    async def execute(self, input_: ListNotesInput) -> ListNotesOutput:
        items, total = await asyncio.gather(
            asyncio.to_thread(self._repository.find_all, input_.limit, input_.offset),
            asyncio.to_thread(self._repository.count),
        )
        return ListNotesOutput(items=items, ...)
```

真の非同期 DB ドライバ（`sqlalchemy.ext.asyncio`、`aiosqlite` 等）を使う場合は `asyncio.to_thread` は不要で `await` を直接使う。

### Runtime 検査の限界

`isinstance(obj, AsyncUseCaseProtocol)` はメソッド名の存在のみを検査する。同期/非同期の区別は `mypy --strict` が静的に保証する。

## 代替案

| 案 | 却下理由 |
|---|---|
| ABC で `AsyncUseCase` 基底クラスを作る | 継承を強制する。Protocol（構造的サブタイピング）の方が柔軟 |
| すべての UseCase を async に統一する | 不要な複雑性。同期リポジトリとの互換性が失われる |
| フレームワーク側に組み込まない | Protocol 定義だけでもフレームワークが「認知」していることが重要 |

## 結果

- 非同期 I/O が必要な UseCase を型で宣言できる
- 同期 UseCase は変更不要（後方互換を維持）
- `asyncio.gather` による並列 I/O が UseCase 層で表現できる
- mypy --strict がコンパイル時に sync/async の混用を検出する
