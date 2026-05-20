# Field Trial 117: TypedDict + @overload による型安全な辞書操作

## テーマ

`TypedDict`（`total=False`、`NotRequired`）で辞書の構造を明示し、
`@overload` で関数のオーバーロードシグネチャを定義するパターンを検証する。
製品 API を例に、サマリー形式・詳細形式・パッチの型を分離する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft117-typeddict/` に以下を実装:

- `ProductSummary`, `ProductDetail`, `ProductPatch` — `TypedDict` で構造を定義
- `SearchFilter` — `NotRequired` フィールドを持つ TypedDict
- `to_summary()` — `@overload` で単一・リスト両対応のシグネチャを定義
- `filter_products()` — `SearchFilter` を受け取るフィルター関数
- 12 テスト通過

## テスト結果

全 12 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `TypedDict` で辞書の構造を明示できる

```python
class ProductSummary(TypedDict):
    product_id: int
    name: str
    price: int

class ProductDetail(TypedDict):
    product_id: int
    name: str
    price: int
    description: str
    stock: int
```

`dict[str, Any]` と違い、アクセス時に mypy が型を検証する。
`ProductDetail` から `ProductSummary` への変換では必要なキーのみ抽出できる。

### O2: `total=False` と `NotRequired` でオプショナルフィールドを定義できる

```python
class ProductPatch(TypedDict, total=False):  # 全フィールドがオプション
    name: str
    price: int

class SearchFilter(TypedDict):
    min_price: NotRequired[int]   # このフィールドだけオプション
    max_price: NotRequired[int]
    in_stock_only: NotRequired[bool]
```

PATCH リクエストのような「すべてオプション」は `total=False`、
一部だけオプションなら `NotRequired` を使い分ける。

### O3: `@overload` で単一・リスト両対応の型を定義できる

```python
@overload
def to_summary(product: ProductDetail) -> ProductSummary: ...

@overload
def to_summary(product: list[ProductDetail]) -> list[ProductSummary]: ...

def to_summary(
    product: ProductDetail | list[ProductDetail],
) -> ProductSummary | list[ProductSummary]:
    if isinstance(product, list):
        return [...]
    return {...}
```

呼び出し側では引数の型から返り値の型が確定するため、`isinstance` チェックが不要になる。

### O4: TypedDict のスプレッドは mypy が完全推論できない

```python
def apply_patch(product: ProductDetail, patch: ProductPatch) -> ProductDetail:
    return {**product, **patch}  # type: ignore[return-value]
```

`TypedDict` の `**kwargs` スプレッドは mypy が `ProductDetail` として推論できない。
`# type: ignore[return-value]` とコメントで理由を残すのが現実的な対処。

## まとめ

FT117 は摩擦ゼロ確認。`TypedDict` + `@overload` は `dict[str, Any]` の
型安全な代替として実用的。スプレッドの型推論（O4）が唯一の制限。
