# 1 つの UseCase、2 つのサーフェス（HTTP + MCP）

NENE2 の看板である **「LLM delivery ready」** とは、同じドメインロジックを、アプリ
向けの JSON HTTP API としても、LLM エージェント向けの
[MCP](https://modelcontextprotocol.io/) ツールとしても提供できる——サーフェスごとに
重複を書かず、一度書くだけ——という意味である。本ページはそれがリファレンスアプリで
どう実現されているかを示す。

## 共有される中核

ドメインロジックは FastAPI も SQLAlchemy も知らない **UseCase** クラスに置かれる
（[`src/example/note/use_case.py`](../../../src/example/note/use_case.py)）。両サーフェス
は *同じ* UseCase を構築し `.execute()` を呼ぶ:

**HTTP** — [`src/example/note/handler.py`](../../../src/example/note/handler.py):

```python
@router.post("", status_code=201, response_model=NoteResponse, summary="Create a note")
async def create_note(body: CreateNoteBody) -> NoteResponse:
    _validate_note_body(body.title, body.body)               # HTTP 境界の関心事
    note = create_use_case.execute(CreateNoteInput(title=body.title, body=body.body))
    return NoteResponse(id=note.id, title=note.title, body=note.body)
```

**MCP** — [`src/example/mcp.py`](../../../src/example/mcp.py):

```python
@server.tool("Create a new note.")
def create_note(title: str, body: str) -> dict:
    return asdict(note_create.execute(CreateNoteInput(title=title, body=body)))
```

同じ `CreateNoteUseCase`、同じ `CreateNoteInput`、同じリポジトリ——違うのは **端
（edge）** だけ。UseCase の `Input`/`Output` DTO が両サーフェスの契約そのものであり、
FastMCP は関数シグネチャからツールスキーマを、FastAPI は Pydantic ボディと
`response_model` から OpenAPI スキーマを導出する。

## これで得られるもの

- ドメインを **一度だけ**書いてテストし、アプリ（HTTP）にもエージェント（MCP）にも
  同じコードパスから届ける。
- UseCase で直したバグは **両サーフェスで同時に**直る。
- 新しいドメインは UseCase が存在した瞬間からエージェントに到達可能になる。`mcp.py`
  は Note / Tag / Comment の 15 ツールを追加の配線なしで公開している。

## 証明（主張ではなくテスト）

[`tests/example/test_http_mcp_parity.py`](../../../tests/example/test_http_mcp_parity.py)
は HTTP アプリと MCP サーバーを **同一** の SQLite ストアに配線し、両サーフェスが
交換可能であることを表明する:

- MCP の `create_note` ツールで作成したノートが `GET /examples/notes/{id}` で読める、
- HTTP の `POST /examples/notes` で作成したノートが MCP の `get_note` ツールで読める、
- どちらの書き込みも 1 つのストアに着地する。

これにより差別化機能をリグレッションテストとして守る——両サーフェスが乖離すれば CI が
落ちる。

## あえて *共有しない* もの

**薄い HTTP 層**は、サーフェス固有の関心事を UseCase の外、端に留める:

| 関心事 | 置き場所 | MCP と共有？ |
|---|---|---|
| Pydantic ボディ検証・`max_length` | `handler.py` の `CreateNoteBody` | 否 |
| 空フィールド拒否 | `handler.py` の `_validate_note_body` | 否 |
| 認証・CORS・スロットリング | `app.py` のミドルウェア | 否 |
| ページネーション解析・RFC 9457 エラー | HTTP 層 | 否 |
| **作成/取得/更新/削除ロジック・not-found 意味論** | **UseCase + エンティティ** | **可** |

これが **API-first / 薄い HTTP 層** の原則の実践である。端が各プロトコルに適合し、
中核がドメインを保持する。実装者への実践的ルール:

> **両**サーフェスで成り立つべきルールは、ハンドラーではなく UseCase かエンティティに
> 置くこと。HTTP ハンドラーに置いた検証は MCP ツールを守らない。

## 関連

- [設計哲学 → LLM Delivery Ready](design-philosophy.md)
- [アーキテクチャ概要](architecture.md)
- [ADR 0011 — MCP をコア依存とする](../../adr/0011-mcp-as-core-dependency.md)
- [MCP サーバーのセットアップ手順](../howto/mcp-setup.md)
