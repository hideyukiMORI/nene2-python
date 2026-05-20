# Field Trial 131: デスクリプタープロトコル

## テーマ

`__get__`, `__set__`, `__delete__`, `__set_name__` を実装したデスクリプターで
バリデーション付きフィールドと遅延評価キャッシュプロパティを FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft131-descriptor/` に以下を実装:

- `PositiveInt` — 正の整数のみを許可するデスクリプター（`__get__`, `__set__`, `__delete__`, `__set_name__`）
- `BoundedStr` — 文字列長を制限するデスクリプター
- `cached_property` — `functools.cached_property` と同等の遅延評価キャッシュ実装
- `Product` クラス — デスクリプターを使ったバリデーション付きフィールド
- `GET /products` — 製品一覧
- `GET /products/{id}/score` — cached_property による価値スコア
- `POST /products` — バリデーションデスクリプター経由で追加
- `PUT /products/{id}/price` — PositiveInt で価格更新
- 21 テスト通過

## テスト結果

全 21 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `__set_name__` でデスクリプターが自動的に属性名を取得できる

```python
class PositiveInt:
    def __set_name__(self, owner: type, name: str) -> None:
        self._name = f"_{name}"  # "price" → "_price" として保存

class Product:
    price = PositiveInt()  # __set_name__(Product, "price") が自動で呼ばれる
```

`__set_name__` は Python 3.6 以降でクラス定義時に自動的に呼ばれる。
これにより、デスクリプターに名前を手動で渡す必要がなくなった。

### O2: `__get__` の `obj is None` ガードでクラス属性アクセスを処理する

```python
def __get__(self, obj: object, objtype: type | None = None) -> int:
    if obj is None:
        return self  # クラス属性としてアクセス時はデスクリプター自身を返す
    return getattr(obj, self._name, 0)
```

`Product.price` のようなクラス属性アクセスでは `obj=None` になる。
`return self` でデスクリプター自身を返すのが慣例。

### O3: `cached_property` はインスタンスの `__dict__` に格納してキャッシュする

```python
class cached_property:
    def __get__(self, obj: object, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        value = self._func(obj)
        obj.__dict__[self._name] = value  # インスタンス __dict__ にキャッシュ
        return value
```

2回目のアクセスではインスタンスの `__dict__` が優先されるため（データデスクリプターより
非データデスクリプターの方が `__dict__` に負ける）、`__get__` は呼ばれなくなる。
`functools.cached_property` と同じメカニズム。

キャッシュのリセットは `obj.__dict__.pop("prop_name", None)` で行う。

### O4: `dataclass(frozen=True)` はデスクリプターと相性が悪い

frozen dataclass は `__setattr__` と `__delattr__` をオーバーライドして
全ての属性変更を禁止するため、デスクリプターの `__set__` が呼ばれず
`FrozenInstanceError` が raise される。

デスクリプターを使う場合は通常の `class` か `dataclass(frozen=False)` を使う。

## まとめ

FT131 は摩擦ゼロ確認。デスクリプタープロトコルを実装することで、
属性アクセス・更新のバリデーションを透過的に挿入できることを確認した。
`cached_property` の遅延評価・`__dict__` キャッシュパターンも実装例として記録する。
