# FT80: MCP E2E — LocalMcpServer + HttpxMcpClient

**日付**: 2026-05-20  
**テーマ**: LocalMcpServer にツールを登録し FastAPI アプリと連携する完全往復の検証  
**バージョン**: v1.8.25  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft80-mcp-e2e/`

---

## 概要

nene2 の MCP 機能（`LocalMcpServer` / `HttpxMcpClient`）を実際に使って
FastAPI アプリと MCP ツールを組み合わせるパターンを検証した。
基本機能は期待通り動作するが、MCP ツールから型付きオブジェクトを返す際の
手動 JSON 変換の要求と、ツール一覧取得 API の欠如が摩擦点として判明した。

---

## 実装パターン

### FastAPI + LocalMcpServer 共存

```python
from nene2.mcp import LocalMcpServer

app = FastAPI()
mcp_server = LocalMcpServer("recipe-assistant", "Recipe management assistant")

@app.post("/recipes")
def create_recipe(body: RecipeBody) -> JSONResponse:
    ...

@mcp_server.tool("Create a new recipe")
def create_new_recipe(title: str, ingredients: list[str]) -> str:
    r = api_client.post("/recipes", json={"title": title, "ingredients": ingredients})
    return r.text  # JSON 文字列を返す
```

### McpHttpError を使ったエラーハンドリング

```python
@mcp_server.tool("Get a recipe by ID")
def get_recipe_by_id(recipe_id: int) -> str:
    r = client.get(f"/recipes/{recipe_id}")
    if r.status_code == 404:
        raise McpHttpError(404, f"Recipe {recipe_id} not found")
    return r.text
```

### HttpxMcpClient をテストトランスポートでモック

```python
transport = httpx.MockTransport(handler=lambda req: httpx.Response(200, json={}))
http_client = HttpxMcpClient(transport=transport)
response = http_client.get("http://testserver", "/recipes")
```

---

## 発見した問題

### 問題1: MCP ツールは文字列しか返せない（手動 JSON 変換が必要）

```python
# ❌ UseCase の Output dataclass を直接返せない
@mcp_server.tool("Get recipe")
def get_recipe() -> RecipeOutput:  # 型エラー
    ...

# ✅ JSON 文字列に変換して返す（手動変換が必要）
@mcp_server.tool("Get recipe")
def get_recipe() -> str:
    output = use_case.execute(input_)
    return json.dumps(dataclasses.asdict(output))
```

UseCase の型安全性が MCP ツール境界で失われる。
FastAPI の `response_model` のような仕組みが MCP にはない。

### 問題2: ツール一覧取得 API がない

```python
mcp_server = LocalMcpServer("test-server")

@mcp_server.tool("Tool 1")
def tool_one() -> str:
    return "one"

# 登録済みツールの確認手段がない
# mcp_server.list_tools()  → 存在しない
# mcp_server.tools          → 存在しない
```

デバッグ時に「このサーバーに何のツールが登録されているか」を確認できない。

### 問題3: Pydantic の `max_items` 非推奨警告

```python
# ⚠ PydanticDeprecatedSince20 警告
ingredients: list[str] = Field(max_items=20)

# ✅ 正しい書き方（nene2 ドキュメントに記載が必要）
ingredients: list[str] = Field(max_length=20)
```

nene2 のドキュメント/例に `max_items` が残っている可能性がある。

---

## テスト結果（全17件パス）

```
test_create_recipe_returns_201              PASSED
test_get_recipe_returns_200                 PASSED
test_get_nonexistent_recipe_returns_404     PASSED
test_list_recipes_empty                     PASSED
test_delete_recipe_returns_204              PASSED
test_mcp_get_all_recipes_returns_json_string  PASSED  # ツールが JSON 文字列を返す
test_mcp_create_recipe_tool                 PASSED
test_mcp_get_recipe_by_id_found             PASSED
test_mcp_get_recipe_by_id_not_found_raises  PASSED  # McpHttpError 正常動作
test_mcp_delete_recipe_tool                 PASSED
test_mcp_delete_nonexistent_raises          PASSED
test_mcp_server_is_importable               PASSED
test_mcp_server_tool_registration           PASSED
test_http_mcp_client_with_test_transport    PASSED  # MockTransport で DI テスト
test_http_mcp_client_raise_for_error        PASSED
test_friction_mcp_tool_cannot_return_typed_object  PASSED
test_friction_no_mcp_tool_discovery_api     PASSED
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F80-1 | MCP ツールは文字列を返す必要があり、UseCase の型付き Output を直接渡せない | 中 |
| F80-2 | LocalMcpServer に登録済みツールの一覧取得 API がない | 低 |
| F80-3 | Pydantic v2 の `max_items` 非推奨（`max_length` に変更必要） | 低 |

---

## 使用感（主観評価）

### 直感性 ★★★★☆

`@mcp_server.tool("description")` デコレーターは非常に直感的で、
FastAPI の `@app.get("/path")` と同じ感覚で使える。
`McpHttpError` と `raise_for_error()` のパターンも明瞭。

### 実害の深刻さ ★★☆☆☆

文字列変換の必要性は設計上仕方ない（MCP プロトコルの制約）。
`json.dumps(dataclasses.asdict(output))` は1行で書けるので実際の摩擦は小さい。
ツール一覧確認はデバッグ時の不便さのみで、本番には影響しない。

### 修正のしやすさ ★★★★★

どれも小さな改善で対応できる:
- `list_tools()` メソッドを `LocalMcpServer` に追加するだけ
- ドキュメントに `json.dumps(dataclasses.asdict(output))` のパターンを記載するだけ

### 総合コメント

MCP 機能は他の Python フレームワークにはない nene2 の差別化ポイント。
FastAPI との共存パターン、`McpHttpError` のエラーハンドリング、
`HttpxMcpClient` の `MockTransport` DI テストパターンは非常によくできている。
「他のフレームワークに乗り換えようと思わない」と思わせる独自の価値がある。

---

## 推奨アクション

1. **Issue**: `LocalMcpServer` に `list_tools()` メソッドを追加（デバッグ用）
2. **minor**: Pydantic v2 の `max_items` → `max_length` への更新（ドキュメント確認）
