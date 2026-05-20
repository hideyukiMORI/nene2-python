# Field Trial 104: AsyncIterator を返す UseCase + StreamingResponse

## テーマ

UseCase が `AsyncIterator` を返し、FastAPI の `StreamingResponse` でストリーミングする本格的なパターンを検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft104-streaming-usecase/` に以下を実装:

- `StreamLogsUseCase` — `AsyncIterator[LogEntry]` を返す UseCase
- `ExportCsvUseCase` — CSV 行を `AsyncIterator[str]` で返す UseCase
- NDJSON / SSE / CSV の 3 形式にストリーミング変換
- 6 テスト通過

## テスト結果

全 6 テスト通過（修正後）。

## Friction Points

### FP1: `TestClient.stream()` 内で `r.text` が使えない

**状況**: `with client.stream("GET", "/export/users.csv") as r:` コンテキスト内で `r.text` にアクセスすると `httpx.ResponseNotRead` が発生する。

```python
# ❌ ResponseNotRead
with client.stream("GET", "/export/csv") as r:
    content = r.text  # エラー!

# ✅ iter_text() でチャンク収集
with client.stream("GET", "/export/csv") as r:
    content = "".join(r.iter_text())
```

**影響**: ストリーミングレスポンスのテストで直感に反するエラーが出る。`streaming.md` How-to に `iter_text()` パターンを追記する必要がある。

### FP2: `AsyncUseCaseProtocol` は `AsyncIterator` を返す UseCase に対応していない

**状況**: `AsyncUseCaseProtocol` は `async def execute(self, input_: I) -> O` を定義しており、`O = AsyncIterator[T]` として使うことは技術的には可能だが、`O` 型が `AsyncIterator` であることを表現するのが難しい。

現在の実装では `AsyncUseCaseProtocol` を使わず、独立した UseCase クラスとして実装した。

**影響**: 低。ストリーミング UseCase は専用の Protocol を定義するか、型注釈なしで書くのが現実的。

## まとめ

FP1 をドキュメント修正で対応。FP2 は将来の検討事項として記録。
