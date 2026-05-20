# FT83: Depends() DI — FastAPI Depends を nene2 アーキテクチャで活用するパターン検証

**日付**: 2026-05-20  
**テーマ**: UseCase・認証・Pagination の Depends 組み合わせパターンと dependency_overrides  
**バージョン**: v1.8.27  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft83-depends-injection/`

---

## 概要

FastAPI の `Depends()` を nene2 の UseCase + Repository パターンと組み合わせた。
依存チェーン（Repository → UseCase → Handler）、認証 Depends、
`PaginationQueryParser` の統合、テスト時の `dependency_overrides` による差し替えを検証した。
`PaginationResponse.model_dump()` が存在しない（`to_dict()` が正しい）という
Pydantic ユーザーがつまずく摩擦点を発見した。

---

## 実装パターン

### Repository → UseCase の Depends チェーン

```python
from typing import Annotated
from fastapi import Depends

def get_repo() -> InMemoryProductRepository:
    return _repo  # シングルトン

def get_list_use_case(
    repo: Annotated[InMemoryProductRepository, Depends(get_repo)],
) -> ListProductsUseCase:
    return ListProductsUseCase(repo)

@app.get("/products")
def list_products(
    use_case: Annotated[ListProductsUseCase, Depends(get_list_use_case)],
) -> JSONResponse:
    products, total = use_case.execute(...)
    return JSONResponse(...)
```

### PaginationQueryParser + UseCase の両方を Depends

```python
@app.get("/products")
def list_products(
    pagination: Annotated[PaginationQueryParser, Depends(PaginationQueryParser)],
    use_case: Annotated[ListProductsUseCase, Depends(get_list_use_case)],
) -> JSONResponse:
    products, total = use_case.execute(
        limit=pagination.limit, offset=pagination.offset
    )
    return JSONResponse(
        PaginationResponse(
            items=[...], total=total, limit=pagination.limit, offset=pagination.offset
        ).to_dict()  # ← model_dump() ではなく to_dict()
    )
```

### 認証 Depends（Bearer Token）

```python
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str | None:
    if credentials is None:
        return None
    return verify_token(credentials.credentials)

def require_auth(user: Annotated[str | None, Depends(get_current_user)]) -> str:
    if user is None:
        raise HTTPException(status_code=401)
    return user

@app.post("/products")
def create_product(
    body: ProductBody,
    use_case: Annotated[CreateProductUseCase, Depends(get_create_use_case)],
    current_user: Annotated[str, Depends(require_auth)],
) -> JSONResponse: ...
```

### テスト時の dependency_overrides

```python
custom_repo = InMemoryProductRepository()
custom_repo.create("Test Product", 100)

app.dependency_overrides[get_repo] = lambda: custom_repo
# テスト実行
del app.dependency_overrides[get_repo]  # クリーンアップ
```

---

## 発見した問題

### 問題1: PaginationResponse.model_dump() が存在しない

```python
# ❌ Pydantic ユーザーは model_dump() を期待してしまう
PaginationResponse(...).model_dump()  # AttributeError!

# ✅ 正しいメソッド
PaginationResponse(...).to_dict()
```

`PaginationResponse` は dataclass だが、Pydantic v2 に慣れているユーザーは
`model_dump()` を期待して AttributeError に直面する。
FastAPI の OpenAPI ドキュメントや response_model を使うには
Pydantic BaseModel にするか、FastAPI の Response 型として登録する必要がある。

### 問題2: Annotated[T, Depends(fn)] の記述が冗長

```python
# 現在の書き方（型情報が Annotated の外側と内側に重複）
def list_products(
    pagination: Annotated[PaginationQueryParser, Depends(PaginationQueryParser)],
    use_case: Annotated[ListProductsUseCase, Depends(get_list_use_case)],
) -> JSONResponse: ...

# 理想（nene2 が型エイリアスを提供）
type PaginationDep = Annotated[PaginationQueryParser, Depends(PaginationQueryParser)]

@app.get("/products")
def list_products(pagination: PaginationDep, ...) -> JSONResponse: ...
```

`PaginationQueryParser` の `Annotated` エイリアスを nene2 が提供すれば
毎回書く冗長さが解消される。

### 問題3: nene2 の認証 Depends ユーティリティがない

```python
# nene2.auth に Depends ユーティリティがない
# ユーザーは HTTPBearer + LocalTokenVerifier を手動で組み合わせる必要がある

# 理想:
from nene2.auth.deps import CurrentUser, require_auth
# これが存在しない
```

`LocalTokenVerifier.from_env()` は実装されているが、
FastAPI の Depends パターンに接続する `CurrentUser` 型や
`require_auth` Depends がない。

---

## テスト結果（全16件パス）

```
test_list_products_empty                        PASSED
test_create_product_returns_201                  PASSED
test_get_product_returns_200                     PASSED
test_get_nonexistent_returns_404                 PASSED
test_create_product_requires_auth                PASSED
test_create_product_with_auth_succeeds           PASSED
test_pagination_with_depends                     PASSED  # PaginationQueryParser Depends 動作
test_pagination_second_page                      PASSED
test_override_repo_with_custom_data              PASSED  # dependency_overrides 動作
test_override_repo_empty                         PASSED
test_request_id_with_depends                     PASSED  # nene2 ミドルウェアと共存
test_security_headers_with_depends               PASSED
test_validation_error_returns_422                PASSED
test_friction_annotated_syntax_verbosity         PASSED  # 摩擦記録
test_friction_use_case_chains_in_depends         PASSED  # 摩擦記録
test_friction_no_nene2_depends_utilities         PASSED  # 摩擦記録
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F83-1 | `PaginationResponse.model_dump()` が存在しない（`to_dict()` が正しい）— Pydantic ユーザー混乱 | 中 |
| F83-2 | `Annotated[PaginationQueryParser, Depends(PaginationQueryParser)]` の冗長記述 | 低 |
| F83-3 | nene2 認証の Depends ユーティリティ (`CurrentUser`, `require_auth`) がない | 低 |

---

## 使用感（主観評価）

### 直感性 ★★★☆☆

`Depends()` のパターン自体は FastAPI の機能なので明確。
ただし Repository → UseCase → Handler の3層チェーンは
Spring/NestJS の DI に慣れたユーザーには違和感がある
（Constructor Injection ではなく Function Injection）。
`dependency_overrides` によるテスト差し替えは非常に優れた機能。

### 実害の深刻さ ★★☆☆☆

`PaginationResponse.to_dict()` を知らなければ AttributeError で即座に詰まる。
nene2 ドキュメントに `PaginationResponse` の使い方が記載されているが、
`model_dump()` と混同するユーザーが続出する可能性がある。

### 修正のしやすさ ★★★★★

- `PaginationResponse` に `model_dump()` の alias を追加（または別名で明記）
- `Annotated[PaginationQueryParser, Depends(PaginationQueryParser)]` を `PaginationDep` 型エイリアスとして公開
- `nene2.auth.deps` モジュールに `CurrentUser` 型と `require_auth` Depends を追加

### 総合コメント

FastAPI の `Depends()` は nene2 のアーキテクチャと非常に相性がよく、
Repository の差し替えも `dependency_overrides` で簡単にできる。
主な摩擦は `PaginationResponse.to_dict()` の名前（Pydantic との不整合）と
認証 Depends ユーティリティの欠如。どちらも小さな追加で解決できる。

---

## 推奨アクション

1. **Issue**: `PaginationResponse` に `model_dump()` エイリアスを追加（Pydantic ユーザー向け）
2. **Issue**: `nene2.http` に `PaginationDep` 型エイリアスを追加（`PaginationQueryParser` の Depends）
3. **Issue**: `nene2.auth.deps` モジュールに認証 Depends ユーティリティを追加
