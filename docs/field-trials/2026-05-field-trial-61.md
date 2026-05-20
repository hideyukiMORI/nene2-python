# FT61: AsyncUseCaseProtocol 実運用検証

**日付**: 2026-05-20  
**テーマ**: 非同期ユースケース (`AsyncUseCaseProtocol`) の実運用確認  
**バージョン**: v1.8.15  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft61-async-usecase/`

---

## 概要

`nene2.use_case.AsyncUseCaseProtocol` を実装したユースケースを FastAPI の async ルートに組み込み、
プロトコル適合・実行時 coroutine 確認・ValidationException 連携を検証した。

---

## 実装内容

- `FetchUserUseCase`: `AsyncUseCaseProtocol[FetchUserInput, FetchUserOutput]` を満たす実装
- `async def execute(input_)`: asyncio.sleep で非同期 I/O を模擬
- `ValidationException.single()` で特定 ID の場合に 422 を返す
- 静的型チェック用のアダプター関数でプロトコル適合を明示

---

## テスト結果

**7/7 passed**

| テスト | 結果 |
|---|---|
| `test_fetch_user_returns_200` | PASSED |
| `test_fetch_nonexistent_user_returns_422` | PASSED |
| `test_use_case_satisfies_protocol` | PASSED |
| `test_execute_is_coroutine_function` | PASSED |
| `test_execute_returns_correct_output` | PASSED |
| `test_execute_raises_on_fail_ids` | PASSED |
| `test_multiple_users_independent` | PASSED |

---

## Friction Points

なし。`AsyncUseCaseProtocol` はプロトコル適合・FastAPI async ルート連携ともに直感的に動作した。

**特筆点**:
- `isinstance(use_case, AsyncUseCaseProtocol)` は `execute` 属性の有無のみチェックするため、
  sync/async 区別は `inspect.iscoroutinefunction()` で補完する必要がある（ADR-0010 で既知）
- `ValidationException.single()` から 422 Problem Details への変換は
  `ErrorHandlerMiddleware` が自動で処理する
- `@runtime_checkable` プロトコルを使った型引数付き型ヒントでも mypy --strict が通る

---

## 結論

`AsyncUseCaseProtocol` は実運用で問題なく使用できる。
FastAPI の async ルートと自然に組み合わせられ、ドメインロジックを HTTP 層から分離する設計が機能している。
