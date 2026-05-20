# Field Trial 14 — AsyncUseCaseProtocol 実運用

**Date:** 2026-05-20
**App:** Weather Dashboard API（複数都市の天気を asyncio.gather で並列取得）
**Directory:** `/home/xi/docker/nene2-python-FT/ft14-async/`
**nene2-python version:** v1.6.0

## 概要

`AsyncUseCaseProtocol` を使った非同期 UseCase を実際に実装し、
`asyncio.gather` による並列 I/O の動作とプロトコルの挙動を検証した。

## 動作確認結果

- `AsyncUseCaseProtocol` の `isinstance` 検査が正しく動くこと ✓
- `asyncio.gather` で 4 都市を並列取得した場合、50ms（直列の場合 200ms）で完了すること ✓
- `FetchDashboardUseCase(fetch_weather: AsyncUseCaseProtocol[...])` のコンストラクタインジェクションが機能すること ✓
- FastAPI の `async def` ハンドラーから非同期 UseCase を `await` で呼び出せること ✓

## 摩擦点

### FT14-F1 (LOW, ドキュメント): runtime_checkable の制限がプロトコルの docstring に記載されていない

`isinstance(sync_obj, AsyncUseCaseProtocol)` が `True` を返す（Python の `@runtime_checkable` は
メソッド名の存在のみを検査し、async/sync を区別しない）。

```python
class FakeSyncWeather:
    def execute(self, input_: WeatherInput) -> str:  # async ではない
        return "fake"

isinstance(FakeSyncWeather(), AsyncUseCaseProtocol)  # → True（注意が必要）
```

この制限は ADR-0010 に記録済みだが、`AsyncUseCaseProtocol` の docstring には記載されていない。
利用者が docstring だけ見て `isinstance` でランタイムガードを書くと誤動作する。

**対応**: プロトコルの docstring に「mypy --strict が静的に保証する; isinstance はメソッド名のみを検査する」旨を追記する。

## まとめ

基本動作は問題なし。`asyncio.gather` パターン・コンストラクタインジェクション・FastAPI 統合のいずれも
摩擦なく動作した。唯一の摩擦は docstring によるドキュメントギャップ（LOW）のみ。

FT14 は「設計が正しく実装されている」ことの確認として有用だった。
