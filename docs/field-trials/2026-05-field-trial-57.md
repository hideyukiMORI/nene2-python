# FT57: AsyncCompositeHealthCheck 実運用検証

**日付**: 2026-05-20  
**テーマ**: 非同期ヘルスチェック集約 (`AsyncCompositeHealthCheck`) と並列実行の実運用確認  
**バージョン**: v1.8.15  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft57-async-health/`

---

## 概要

`nene2.http.AsyncCompositeHealthCheck` を FastAPI の async ルートに組み込み、
複数の依存サービス（DB・外部API）のヘルスチェックを `asyncio.gather` で並列実行するパターンを検証した。

---

## 実装内容

- `AsyncDatabaseHealthCheck` / `AsyncExternalApiHealthCheck`: `AsyncHealthCheckProtocol` 実装クラス（`async def check()`）
- `AsyncCompositeHealthCheck([db, api])`: `asyncio.gather` による並列集約
- `/health` エンドポイント: `async def health()` で `await composite.check()` を呼び出し
- 並列実行タイミングテスト: 各 50ms のチェック2つが 90ms 未満で完了することを確認

---

## テスト結果

**5/5 passed**

| テスト | 結果 |
|---|---|
| `test_all_healthy_returns_200` | PASSED |
| `test_db_unhealthy_returns_503` | PASSED |
| `test_api_unhealthy_returns_503` | PASSED |
| `test_both_unhealthy_returns_503` | PASSED |
| `test_parallel_execution_is_faster` | PASSED |

---

## Friction Points

なし。`AsyncCompositeHealthCheck` は直感的なインターフェースで、並列実行も確認できた。
`pytest-asyncio` の `asyncio_mode = "auto"` 設定で `async def test_*` がそのまま動作した。

---

## 結論

`AsyncCompositeHealthCheck` は実運用で問題なく使用できる。
`asyncio.gather` による並列実行は計測でも確認でき、直列実行比で約2倍の高速化が得られた。
