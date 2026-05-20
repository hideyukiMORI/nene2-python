# FT71: 完全レイヤードアーキテクチャ実運用検証

**日付**: 2026-05-20  
**テーマ**: UseCaseProtocol + Repository パターンによる完全レイヤードアーキテクチャ検証  
**バージョン**: v1.8.19  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft71-layered-arch/`

---

## 概要

NENE2 の核心設計パターン（HTTP Handler → UseCase → Repository の完全分離）を
Todo ドメインで実装し、`UseCaseProtocol`・`ValidationException`・`InMemoryRepository` 注入が
実運用で問題なく動作することを確認した。

---

## 実装内容

### ドメイン層（HTTP・DB 非依存）
- `Todo(id, title, done)` — `dataclass(frozen=True, slots=True)` 値オブジェクト
- Input/Output DTO 群 — `CreateTodoInput/Output`, `GetTodoInput/Output`, `ListTodosInput/Output`, `CompleteTodoInput/Output`
- `TodoRepositoryInterface` — `abc.ABC` 抽象インターフェース
- UseCase 群: `CreateTodoUseCase`, `GetTodoUseCase`, `ListTodosUseCase`, `CompleteTodoUseCase`

### インフラ層
- `InMemoryTodoRepository` — テスト用インメモリ実装
- `SqlAlchemyTodoRepository` — 本番用 SQLAlchemy 実装

### HTTP 層（thin handler）
- `create_app(repository=None)` — `repository` が None の場合 SQLAlchemy を使用、注入された場合はそのまま使用
- Handler は parse → use-case → response の 3 ステップのみ

---

## テスト結果

**15/15 passed**

| テスト | 結果 | 種別 |
|---|---|---|
| `test_create_todo_use_case_returns_new_todo` | PASSED | UseCase 単体 |
| `test_create_todo_use_case_raises_validation_error_on_blank_title` | PASSED | UseCase 単体 |
| `test_get_todo_use_case_returns_existing_todo` | PASSED | UseCase 単体 |
| `test_list_todos_use_case_returns_all_items` | PASSED | UseCase 単体 |
| `test_complete_todo_use_case_marks_done` | PASSED | UseCase 単体 |
| `test_list_todos_returns_paginated` | PASSED | HTTP 統合 |
| `test_get_todo_returns_200` | PASSED | HTTP 統合 |
| `test_get_nonexistent_todo_returns_404` | PASSED | HTTP 統合 |
| `test_create_todo_returns_201` | PASSED | HTTP 統合 |
| `test_create_todo_with_blank_title_returns_422` | PASSED | HTTP 統合 |
| `test_complete_todo_marks_done` | PASSED | HTTP 統合 |
| `test_complete_nonexistent_todo_returns_404` | PASSED | HTTP 統合 |
| `test_list_todos_pagination_offset` | PASSED | HTTP 統合 |
| `test_request_id_header_present` | PASSED | HTTP 統合 |
| `test_in_memory_repo_used_for_unit_tests_without_db` | PASSED | DI 注入 |

---

## Friction Points

なし。

**特筆点**:
- `ValidationException` を UseCase 内（ドメイン層）で raise しても、
  `ErrorHandlerMiddleware` が自動で 422 Problem Details に変換する。
  ドメイン層が HTTP を知らなくてよい。
- `create_app(repository=InMemoryTodoRepository(...))` の DI 注入パターンで
  HTTP テストも DB なしで実行できる。5 つの UseCase 単体テストは完全に DB 非依存。
- `UseCaseProtocol[I, O]` の静的型チェックは `isinstance()` ではなく型注釈で行う。
  `def _assert_protocols() -> None: _: UseCaseProtocol[...] = SomeUseCase(...)` のパターンで
  mypy が protocol 適合を静的に保証する。
- `InMemoryTodoRepository` の `mark_done()` 実装で `done=True` に更新するため
  リスト全体を再構築するパターン（frozen dataclass なので in-place 変更不可）が自然に強制される。

---

## 結論

`UseCaseProtocol` + `Repository Interface` + `InMemoryRepository` の三点セットで
NENE2 の完全レイヤードアーキテクチャが機能する。
UseCase 単体テスト（DB なし）と HTTP 統合テスト（SQLAlchemy 経由）を
同一 `create_app()` ファクトリで切り替えられる DI パターンが特に有用。
