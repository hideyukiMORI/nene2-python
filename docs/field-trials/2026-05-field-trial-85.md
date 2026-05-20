# FT85: OpenAPI スキーマ品質 — JSONResponse と response_model の摩擦

**日付**: 2026-05-20  
**テーマ**: JSONResponse を返すと OpenAPI スキーマが Any になる問題と正しいパターン検証  
**バージョン**: v1.8.29  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft85-openapi-schema/`

---

## 概要

nene2 のハンドラーは `JSONResponse` を返すが、`response_model` を省略すると
OpenAPI スキーマに型情報が含まれず Swagger UI が使いにくくなる。
CLAUDE.md には「`response_model` で明示（`Any` 返却禁止）」と書かれているが、
`JSONResponse` との組み合わせ方が示されていない。
3つのパターン（response_model なし / あり / Pydantic 直返し）を検証した。

---

## 3パターンの比較

### パターン1: response_model なし（❌ 非推奨）

```python
@app.get("/articles/{article_id}")
def get_article(article_id: int) -> JSONResponse:
    return JSONResponse({"article_id": 1, "title": "..."})
```

- OpenAPI スキーマ: `{}` または `{"title": "Response"}`（型情報なし）
- Swagger UI: レスポンス例なし、フィールド定義なし
- 型安全性: なし

### パターン2: response_model あり（✅ nene2 推奨）

```python
class ArticleResponse(BaseModel):
    article_id: int = Field(description="記事 ID")
    title: str = Field(max_length=200, description="記事タイトル")
    ...

@app.get(
    "/articles/{article_id}",
    response_model=ArticleResponse,
    responses={404: {"description": "Article not found"}},
    summary="記事を取得する",
    tags=["articles"],
)
def get_article(article_id: int) -> JSONResponse:
    if article_id not in _articles:
        return problem_details_response(...)  # nene2 パターン維持
    return JSONResponse({...})
```

- OpenAPI スキーマ: `ArticleResponse` の完全な型情報
- Swagger UI: フィールド説明・型・例が表示される
- nene2 の `problem_details_response()` と共存可能

### パターン3: Pydantic モデルを直接返す

```python
@app.get("/articles/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int) -> ArticleResponse:
    if article_id not in _articles:
        raise HTTPException(404, "Not found")  # ← nene2 スタイルではない
    return ArticleResponse(...)
```

- OpenAPI スキーマ: 最も完全
- 型安全性: 最高（戻り値が検証される）
- 問題: nene2 の `problem_details_response()` が使えない

---

## 発見した問題

### 問題1: JSONResponse + response_model の組み合わせが未文書

```python
# nene2 ユーザーはこれが正しい書き方だと知らない
@app.get("/articles/{id}", response_model=ArticleResponse)
def get_article(id: int) -> JSONResponse:  # ← 戻り値型と response_model が一致しない
    return JSONResponse({...})

# response_model は OpenAPI スキーマ生成のみに使われ、
# JSONResponse の内容は response_model でバリデーションされない
```

`response_model` と `JSONResponse` の組み合わせは動作するが、
FastAPI は `JSONResponse` の内容を `response_model` で検証しない。
「`response_model` を指定すれば内容も検証される」と誤解するユーザーがいる。

### 問題2: Pydantic レスポンスモデルと Domain dataclass の二重定義

```python
@dataclass(frozen=True, slots=True)
class Article:
    article_id: int
    title: str
    body: str
    author: str

class ArticleResponse(BaseModel):
    article_id: int = Field(description="記事 ID")
    title: str = Field(max_length=200, description="記事タイトル")
    body: str = Field(...)
    author: str = Field(...)
```

Domain オブジェクトと API スキーマオブジェクトを両方定義する必要があり、
フィールドを変更すると両方を更新しなければならない。

### 問題3: problem_details_response() と Pydantic 直返しの非一貫性

```python
# パターン2 (JSONResponse): nene2 スタイルの 404
@app.get("/articles/{id}", response_model=ArticleResponse)
def get_article_v2(id: int) -> JSONResponse:
    if id not in _articles:
        return problem_details_response("not-found", ..., 404, ...)  # ✅ RFC 9457
    return JSONResponse({...})

# パターン3 (Pydantic 直返し): FastAPI スタイルの 404
@app.get("/articles/{id}", response_model=ArticleResponse)
def get_article_v3(id: int) -> ArticleResponse:
    if id not in _articles:
        raise HTTPException(404)  # ❌ {"detail": "Not found"} になる（nene2 スタイルではない）
    return ArticleResponse(...)
```

Pydantic モデルを直接返す場合は `problem_details_response()` を使えず、
`HTTPException` を raise する必要がある。
これは nene2 の Problem Details ポリシーと矛盾する。

---

## テスト結果（全16件パス）

```
test_no_schema_create_returns_201                     PASSED
test_no_schema_get_returns_200                        PASSED
test_no_schema_openapi_get_has_no_response_schema     PASSED  # スキーマなし確認
test_with_schema_create_returns_201                   PASSED
test_with_schema_get_returns_200                      PASSED
test_with_schema_list_returns_200                     PASSED
test_with_schema_openapi_has_response_schema          PASSED  # スキーマあり確認
test_with_schema_openapi_has_tags                     PASSED  # tags 反映
test_with_schema_openapi_has_summary                  PASSED  # summary 反映
test_with_schema_404_returns_problem_details          PASSED  # nene2 404 と共存
test_pydantic_return_get_returns_200                  PASSED
test_pydantic_return_openapi_has_schema               PASSED
test_friction_json_response_loses_schema              PASSED  # 摩擦記録
test_friction_response_model_does_not_validate        PASSED  # 摩擦記録
test_friction_problem_details_and_pydantic_conflict   PASSED  # 摩擦記録
test_friction_duplicate_type_definition               PASSED  # 摩擦記録
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F85-1 | `JSONResponse` + `response_model` の正しい組み合わせ方がドキュメントに未記載 | 中 |
| F85-2 | Domain dataclass と Pydantic レスポンスモデルの二重定義が避けられない | 低 |
| F85-3 | Pydantic 直返しパターンでは `problem_details_response()` が使えない（HTTPException と非一貫） | 中 |

---

## 使用感（主観評価）

### 直感性 ★★★☆☆

`JSONResponse` + `response_model` のパターンは直感的ではない。
「`JSONResponse` を返すと戻り値型が `JSONResponse` なのに `response_model=ArticleResponse` と
書く」という不整合に戸惑う。FastAPI のドキュメントを読めば理解できるが、
nene2 のコンテキストでの説明がない。

### 実害の深刻さ ★★★☆☆

`response_model` を省略すると Swagger UI に型情報が出ず、
API クライアント（TypeScript, Kotlin 等）の自動生成コードに型が付かない。
実際の運用では非常に不便で、フロントエンドチームから「なぜ型がないの?」と言われる。

### 修正のしやすさ ★★★★★

コード修正は不要。必要なのはドキュメントだけ:
- nene2 how-to: `JSONResponse` + `response_model` の正しいパターン例
- `response_model` がバリデーションではなく OpenAPI スキーマ生成のみに使われることの説明
- `problem_details_response()` との共存パターン

### 総合コメント

「`JSONResponse` を使いながら完全な OpenAPI スキーマを生成する」パターンは
FastAPI の機能で実現できるが、nene2 のドキュメントに記載がない。
CLAUDE.md には「`response_model` で明示」と書かれているが、
例コード（example app）が `response_model` を使っていない矛盾もある。
コード修正なしでドキュメントだけで対応できる摩擦点。

---

## 推奨アクション

1. **docs**: how-to ガイドに「OpenAPI スキーマを整備する」記事を追加
   — `response_model=PydanticModel` + `def handler() -> JSONResponse` パターン
   — `problem_details_response()` との共存例
2. **refactor**: `example/` ハンドラーに `response_model` を追加して CLAUDE.md ポリシーに準拠させる
