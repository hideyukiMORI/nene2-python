# ADR-0004: AI-First 設計原則

- **Status**: Accepted
- **Date**: 2026-05-19

---

## Context

このフレームワークは「LLM delivery ready」を設計目標の一つとしている。AI エージェント（Claude 等）がコードを正確に読み・書き・テストできることを設計上の要件とする。また、UseCase を MCP ツールとして公開することで、AI エージェントがアプリケーションのビジネスロジックを直接実行できるようにする。

---

## Decision

### 1. AI が読みやすいコード構造

**ファイル単位で 1 責務を徹底する**

LLM はコンテキストウィンドウに収まる単位でコードを処理する。1 ファイルが 300 行を超えると、全体像を一度に把握できなくなる。

```
note/
  entity.py    → Note エンティティのみ
  repository.py → NoteRepositoryInterface + InMemoryNoteRepository
  use_case.py  → ListNotesUseCase / GetNoteUseCase / CreateNoteUseCase
  handler.py   → HTTP ルーター
```

**明示的な型で意図を伝える**

```python
# LLM が即座に理解できる
def execute(self, input_: CreateNoteInput) -> Note: ...

# LLM が推測が必要
def execute(self, data: dict) -> dict: ...
```

**略語・魔法の値を使わない**

```python
# OK
MAX_PAGINATION_LIMIT: int = 100

# NG
MAX = 100
```

### 2. OpenAPI スキーマの充実

FastAPI が生成する OpenAPI ドキュメントは LLM が API を呼び出す際の唯一の参照先となる。

```python
# OK — LLM が API を理解できる
@router.post(
    "",
    status_code=201,
    summary="Create a new note",
    description="Creates a note with title and body. Returns the created note.",
    response_model=NoteResponse,
    responses={
        422: {"description": "Validation failed"},
    },
)
async def create_note(body: CreateNoteBody) -> NoteResponse: ...

class CreateNoteBody(BaseModel):
    title: str = Field(max_length=200, description="Note title (non-empty)")
    body: str = Field(max_length=10000, description="Note body in plain text")

# NG — スキーマが不明確
@router.post("")
async def create_note(body: CreateNoteBody) -> JSONResponse: ...
```

### 3. UseCase を MCP ツールとして再利用する設計

UseCase は HTTP に依存しないため、MCP ツールとしてそのまま公開できる。

```
HTTP Request → Handler → UseCase.execute(Input) → Output → HTTP Response
MCP Call     → MCP Tool → UseCase.execute(Input) → Output → MCP Response
```

実装時の方針:
- `src/nene2/mcp/` 以下に MCP ツール定義を配置
- `UseCase.execute()` の Input/Output を MCP ツールの引数・返り値に直接マッピング
- 追加のロジックを MCP レイヤーに持ち込まない

### 4. 引き継ぎドキュメントの整合性

新しいドメインやユースケースを追加した場合は以下を同時に更新する:
1. `CLAUDE.md` の「プロジェクトレイアウト」セクション（追加があれば）
2. OpenAPI スキーマ（FastAPI が自動生成するが、`summary`/`description` を手で書く）
3. 必要に応じて `docs/adr/` に設計決定を記録

### 5. テストが LLM の仕様書になる

テスト名は「仕様の文章」として読めるように書く。

```python
# OK — 仕様が読める
def test_returns_404_when_note_not_found() -> None: ...
def test_returns_422_when_title_is_empty() -> None: ...
def test_paginates_results_with_offset_and_limit() -> None: ...

# NG — 何をテストしているか不明
def test_get_note() -> None: ...
def test_error() -> None: ...
```

---

## Consequences

- 新しいエンドポイントは必ず `response_model` を宣言する（`JSONResponse` を直接返す場合は `NoteResponse` の TypedDict 等を用意する）
- UseCase の Input/Output は `dataclass(frozen=True)` とし、HTTP 固有の型（`Request`, `Response`）を含まない
- MCP 対応実装時のリファクタリングコストを最小化できる
- コードベース全体を LLM が一度に読めないため、ディレクトリ構造とファイル名が「インデックス」の役割を果たす
