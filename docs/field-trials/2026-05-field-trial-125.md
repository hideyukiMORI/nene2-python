# Field Trial 125: Python 3.12+ ジェネリッククラスと Pydantic Generic モデル

## テーマ

Python 3.12 の新構文 `class Foo[T]` でジェネリックデータクラスを定義し、
Pydantic の `Generic[T]` と組み合わせて型安全なレスポンスラッパーを実装するパターンを検証する。
`PaginationResponse[T]` スタイルのジェネリック設計を実際に動かして確認する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft125-generic-response/` に以下を実装:

- `Page[T]` — Python 3.12 新構文のジェネリックデータクラス（`page`, `has_next`, `map()` メソッド）
- `ApiResponse(BaseModel, Generic[T])` — Pydantic ジェネリックモデル
- `PaginatedResponse(BaseModel, Generic[T])` — ページネーション Pydantic モデル
- `paginate[ItemT]()` — Python 3.12 新構文のジェネリック関数
- 11 テスト通過

## テスト結果

全 11 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: Python 3.12 新構文 `class Foo[T]` でジェネリッククラスを宣言できる

```python
@dataclass(frozen=True, slots=True)
class Page[T]:
    items: tuple[T, ...]
    total: int

    def map[U](self, func: ...) -> "Page[U]":
        ...
```

`TypeVar` を明示しなくてよく、シグネチャが読みやすい。
メソッドに別の型変数 `[U]` を持たせることも可能。

### O2: Pydantic モデルのジェネリックは `Generic[T]` 継承で定義する

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    data: T
    success: bool = True

response = ApiResponse[Product](data=product)
response.model_dump()  # {"data": {...}, "success": True, ...}
```

Python 3.12 新構文と Pydantic の Generic 継承は混在できる（`TypeVar` は Pydantic 側で使用）。

### O3: `map()` メソッドでジェネリック変換が型安全に書ける

```python
page: Page[Product] = paginate(products, page=1, per_page=5)
summary_page: Page[ProductSummary] = page.map(lambda p: ProductSummary(...))
```

`Page[T]` の `map[U]()` メソッドで `Page[Product]` → `Page[ProductSummary]` を変換できる。
`items` タプルを使い回すため新しいページオブジェクトを作成するだけで済む。

## まとめ

FT125 は摩擦ゼロ確認。Python 3.12+ の新構文でジェネリッククラスを宣言する方法と、
Pydantic `Generic[T]` の組み合わせを確認した。
nene2 の `PaginationResponse` は既に Pydantic ジェネリックとして実装されており、
このパターンはそれと整合する設計。
