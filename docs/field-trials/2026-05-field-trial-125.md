# Field Trial 125: Python 3.12 ジェネリッククラス + Pydantic Generic

## テーマ

Python 3.12 の新しいジェネリック構文 (`class Foo[T]`, `def func[T]()`) と
Pydantic の `Generic[T]` を組み合わせたページネーション・レスポンスラッパーを
FastAPI エンドポイントで検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft125-generic-response/` に以下を実装:

- `Page[T]` — Python 3.12 新構文 `class Page[T]` の frozen dataclass
  - `has_next`, `page_count` プロパティ
  - `map[U](func)` メソッドでエンティティ変換
- `paginate[ItemT]()` — Python 3.12 新構文のジェネリック関数
- `ApiResponse[T]` — Pydantic `BaseModel` + `Generic[T]`（成功・失敗ラッパー）
- `PaginatedResponse[T]` — Pydantic `BaseModel` + `Generic[T]`（ページネーション）
- `GET /products` — `PaginatedResponse[Product]` 返却
- `GET /products/summary` — `Page[Product].map()` でエンティティ変換
- `GET /products/{product_id}` — `ApiResponse[Product]` / `ApiResponse[str]` 返却
- 10 テスト通過

## テスト結果

全 10 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: Python 3.12 の `class Foo[T]` 構文は dataclass と組み合わせられる

```python
@dataclass(frozen=True, slots=True)
class Page[T]:
    items: tuple[T, ...]
    total: int
    page: int
    per_page: int

    def map[U](self, func: object) -> "Page[U]":
        ...
```

`TypeVar` 宣言が不要で、クラス定義がシンプルになる。
メソッドも `def map[U](self, ...)` と型パラメーターを宣言できる。
`@dataclass` デコレーターと完全に互換性がある。

### O2: Pydantic の `Generic[T]` は依然として `TypeVar` が必要

```python
T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    data: T
    success: bool = True
    message: str = ""
```

Python 3.12 の新構文 (`class ApiResponse[T](BaseModel)`) は Pydantic v2 では
未対応。`TypeVar` + `Generic[T]` の従来の書き方が必要。

### O3: `Page[T].map()` でレスポンス変換を型安全に行える

```python
page_result: Page[Product] = paginate(products, page, per_page)
summary_page: Page[ProductSummary] = page_result.map(
    lambda p: ProductSummary(product_id=p.product_id, name=p.name)
)
```

`map()` はページネーションメタデータ（total, page, per_page）を保持したまま
アイテムの型だけ変換できる。エンティティを API レスポンス用 DTO に変換する
パターンとして有用。

## まとめ

FT125 は摩擦ゼロ確認。Python 3.12 の新しいジェネリック構文と Pydantic の
`Generic[T]` を使い分けるパターンを確認した。
