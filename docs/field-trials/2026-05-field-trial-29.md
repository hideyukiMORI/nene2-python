# FT29: AsyncUseCaseProtocol 実運用検証

**日付**: 2026-05-20
**テーマ**: `AsyncUseCaseProtocol` を使った非同期 UseCase パターンの実運用検証
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft29-async-usecase/`

---

## 目的

`AsyncUseCaseProtocol` の実装・FastAPI ハンドラーへの統合・並行処理の動作を検証する。

---

## 実施内容

- 外部 API 呼び出しを模した `FetchDataUseCase` を実装
- `asyncio.gather()` で並行実行を確認
- Protocol 適合性と isinstance() の既知制限を検証

---

## テスト結果

### test_app.py（正常系・機能確認）
| テスト | 結果 |
|---|---|
| test_get_item_returns_200 | PASS |
| test_slow_endpoint_returns_200 | PASS |
| test_async_use_case_executes_correctly | PASS |
| test_async_use_case_satisfies_protocol | PASS |
| test_multiple_async_calls_are_independent | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_isinstance_cannot_distinguish_sync_vs_async_protocol | PASS | 既知（ADR-0010） |
| test_no_async_usecase_base_class_provided | PASS | 軽微（設計通り） |
| test_no_generic_di_container_for_async_use_cases | PASS | あり（ドキュメント不備） |

---

## 発見した摩擦点

### FT29-F1: FastAPI Depends を使った AsyncUseCase DI パターンがドキュメント化されていない

**概要**: `AsyncUseCaseProtocol` を FastAPI の依存性注入と統合する標準的なパターンがない。
ユーザーは毎回自分でパターンを決める必要がある。

```python
# ユーザーが毎回書く必要があるボイラープレート
def get_fetch_use_case() -> FetchDataUseCase:
    return FetchDataUseCase()

@app.get("/items/{item_id}")
async def get_item(
    item_id: int,
    use_case: FetchDataUseCase = Depends(get_fetch_use_case),
) -> JSONResponse:
    result = await use_case.execute(FetchDataInput(item_id=item_id))
    ...
```

**判断**: how-to ドキュメントに DI パターンを追記する（Issue 化）。

---

## まとめ

`AsyncUseCaseProtocol` の基本機能（実装・FastAPI 統合・並行処理）は問題なく動作する。

摩擦点:
1. **AsyncUseCase + FastAPI DI パターンがドキュメント化されていない** → Issue 化・how-to に追記
2. **isinstance() の sync/async 区別不可** → ADR-0010 記載の既知制限、修正不要
