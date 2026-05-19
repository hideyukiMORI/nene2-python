# ADR-0002: クリーンアーキテクチャの採用

- **Status**: Accepted
- **Date**: 2026-05-19

---

## Context

Web アプリケーションは HTTP フレームワークと DB ライブラリに密結合しやすい。この密結合は以下の問題を引き起こす:
- UseCase のテストに HTTP サーバーや DB が必要になる
- フレームワーク変更時のリライトコストが高い
- LLM がコードを解析する際に責務の境界が不明確になる

PHP 版 NENE2 で検証済みの「薄い HTTP 層」アーキテクチャを Python でも採用する。

---

## Decision

### レイヤー構造

```
[HTTP Layer]  FastAPI Router / Handler
     ↓ Input DTO (Pydantic BaseModel)
[Application] UseCase
     ↓ Domain Entity
[Domain]      Entity (dataclass frozen+slots) / RepositoryInterface (ABC)
     ↓ implements
[Infra]       ConcreteRepository (SQLite / MySQL / InMemory)
```

### レイヤー間の依存ルール

- **上位レイヤーは下位レイヤーに依存してよい**
- **下位レイヤーは上位レイヤーに依存してはならない**
- `UseCase` は `fastapi`, `sqlalchemy` を import してはならない
- `Entity` は `pydantic`, `fastapi` を import してはならない

### ファイル構造

各ドメイン（例: `note`）は以下のファイルのみ持つ:

```
note/
  entity.py       — dataclass(frozen=True, slots=True)
  repository.py   — ABC（Interface のみ）+ InMemory 実装
  use_case.py     — UseCase クラス群（Input/Output DTO 含む）
  handler.py      — FastAPI ルーター（薄い: parse → use-case → response）
```

Concrete DB Repository は `note/infrastructure/` に配置する（実装時）。

### DI（依存性の注入）

- コンストラクタインジェクションを使用
- FastAPI の `Depends()` は **HTTP 境界のみ**使用する
- UseCase のインスタンス生成は `app.py` のファクトリで行う

```python
# OK: HTTP境界でのDI
def make_note_router(
    list_use_case: ListNotesUseCase,
    get_use_case: GetNoteUseCase,
    create_use_case: CreateNoteUseCase,
) -> APIRouter: ...

# NG: UseCase内でFastAPIに依存
class CreateNoteUseCase:
    def __init__(self, db: Session = Depends(get_db)) -> None: ...  # 禁止
```

### UseCase の設計ルール

- 1 UseCase = 1 ユースケース（単一責務）
- `execute(input_: XxxInput) -> XxxOutput` を必ず実装
- UseCase は他の UseCase を呼び出さない
- UseCase 内でのロギングは `logging.getLogger(__name__)` のみ使用

---

## Consequences

- HTTP ハンドラーのテストなしに UseCase のテストが書ける
- DB を InMemory に差し替えることでドメインテストが高速に実行できる
- MCP ツールとして UseCase を再利用する際に HTTP レイヤーが不要になる（MCP 対応の前提）
- handler.py が肥大化したら UseCase に責務を移す（ルール: handler は 30 行以内）
