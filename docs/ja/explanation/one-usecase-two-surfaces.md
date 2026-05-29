# 1 つの UseCase、2 つのサーフェス（HTTP + MCP）

NENE2 の看板である **「LLM delivery ready」** とは、同じドメインロジックを、アプリ
向けの JSON HTTP API としても、LLM エージェント向けの
[MCP](https://modelcontextprotocol.io/) ツールとしても提供できる——サーフェスごとに
重複を書かず、一度書くだけ——という意味である。本ページはそれがリファレンスアプリで
どう実現されているかを示す。

## 共有される中核

ドメインロジックは FastAPI も SQLAlchemy も知らない **UseCase** クラスに置かれる
（[`src/example/note/use_case.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/note/use_case.py)）。両サーフェス
は *同じ* UseCase を構築し `.execute()` を呼ぶ:

**HTTP** — [`src/example/note/handler.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/note/handler.py):

```python
@router.post("", status_code=201, response_model=NoteResponse, summary="Create a note")
async def create_note(body: CreateNoteBody) -> NoteResponse:
    note = create_use_case.execute(CreateNoteInput(body.title, body.body))
    return NoteResponse(id=note.id, title=note.title, body=note.body)
```

ハンドラーは純粋に *parse → use-case → response* であり、ドメイン規則を持たない。
長さ・非空のチェックは `CreateNoteInput`（後述）にあり、どのサーフェスから呼ばれても
成り立つ。

**MCP** — [`src/example/mcp.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/src/example/mcp.py):

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

[`tests/example/test_http_mcp_parity.py`](https://github.com/hideyukiMORI/nene2-python/blob/main/tests/example/test_http_mcp_parity.py)
は HTTP アプリと MCP サーバーを **同一** の SQLite ストアに配線し、両サーフェスが
交換可能であることを表明する:

- MCP の `create_note` ツールで作成したノートが `GET /examples/notes/{id}` で読める、
- HTTP の `POST /examples/notes` で作成したノートが MCP の `get_note` ツールで読める、
- どちらの書き込みも 1 つのストアに着地する。

これにより差別化機能をリグレッションテストとして守る——両サーフェスが乖離すれば CI が
落ちる。

## 共有するもの・しないもの

境界線は **ドメイン規則 か 転送機構 か**。ノートに「どう届いたかに関わらず」成り立つ
べきことは UseCase の Input DTO に置かれ、両サーフェスで強制される。プロトコルの
配管は端に留まる。

| 関心事 | 置き場所 | MCP と共有？ |
|---|---|---|
| 長さ上限（`max_length`）・非空 | `use_case.py` の `CreateNoteInput.__post_init__` | **可** |
| 作成/取得/更新/削除ロジック・not-found 意味論 | UseCase + エンティティ | **可** |
| リクエスト解析・引数の形/型 | Pydantic ボディ（HTTP）/ FastMCP シグネチャ（MCP） | 各サーフェス固有 |
| 認証・CORS・スロットリング | `app.py` のミドルウェア | 否 |
| ページネーション解析・RFC 9457 エラー整形 | HTTP 層 | 否 |

HTTP の `CreateNoteBody` は同じ `MAX_NOTE_TITLE_LENGTH` 定数で `max_length` を映す
——上限は一度だけ宣言され、OpenAPI に文書化され、*かつ* MCP 経路のためにドメインで
強制される。

これが **API-first / 薄い HTTP 層** の原則の実践である。端が各プロトコルに適合し、
中核がドメインを保持する。実装者への実践的ルール:

> **両**サーフェスで成り立つべきルールは、ハンドラーではなく UseCase かエンティティに
> 置くこと。HTTP ハンドラーにしか無いチェックは MCP ツールを守らない。（長さ・非空の
> チェックを Input DTO に移したのはまさにこのため——パリティテスト参照。）

## 関連

- [設計哲学 → LLM Delivery Ready](design-philosophy.md)
- [アーキテクチャ概要](architecture.md)
- [ADR 0011 — MCP をコア依存とする](../../adr/0011-mcp-as-core-dependency.md)
- [MCP サーバーのセットアップ手順](../howto/mcp-setup.md)
