# Field Trial 129: functools モジュールの高度な活用

## テーマ

`partial`, `reduce`, `wraps`, `singledispatch` を使った
部分適用・集計・デコレーター・型ディスパッチを FastAPI エンドポイントで検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft129-functools/` に以下を実装:

- `functools.partial` — 割引率を固定した `apply_10pct`, `apply_20pct`, `apply_30pct`
- `functools.reduce` — 価格リストの合計・最大値計算
- `functools.wraps` — 実行時間計測デコレーター（メタデータ保持を確認）
- `functools.singledispatch` — `int`/`float`/`list`/`bool`/`str` の型別フォーマット
- `GET /discount/{price}` — partial で割引計算
- `POST /cart/total` — reduce でカート合計
- `GET /fibonacci/{n}` — wraps デコレーター適用関数
- `GET /timing-log` — デコレーター計測ログ
- `GET /format` — singledispatch で型別フォーマット
- 24 テスト通過

## テスト結果

全 24 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `functools.partial` でコンフィギュレーション済み関数を生成できる

```python
def apply_discount(price: int, rate: float) -> int:
    return int(price * (1 - rate))

apply_10pct = functools.partial(apply_discount, rate=0.10)
apply_20pct = functools.partial(apply_discount, rate=0.20)

apply_10pct(1000)  # 900
apply_20pct(1000)  # 800
```

設定値ごとに関数を作るより `partial` のほうが DRY。
`dict[str, Callable]` に入れてルーティングするパターンとも相性が良い。

### O2: `functools.wraps` でデコレーターがメタデータを保持できる

```python
def timing_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)  # __name__, __doc__ etc. をコピー
    def wrapper(*args: object, **kwargs: object) -> object:
        ...
    return wrapper

@timing_decorator
def compute_fibonacci(n: int) -> int: ...

compute_fibonacci.__name__  # "compute_fibonacci" (wrapperではない)
```

`@wraps` なしだと `__name__` が `"wrapper"` になり、ログ・デバッグが困難。
FastAPI の依存注入とも相性が良い（ルート名が wrapper になるとドキュメント品質が下がる）。

### O3: `functools.singledispatch` で型ごとの処理を分岐できる

```python
@functools.singledispatch
def format_value(value: object) -> str:
    return str(value)

@format_value.register
def _(value: int) -> str:
    return f"{value:,}"

@format_value.register
def _(value: bool) -> str:
    return "yes" if value else "no"
```

`bool` は `int` のサブクラスなので、`bool` の実装を `int` より後に登録すると
`int` の実装が優先されてしまう。Python は MRO 順で最初にマッチしたものを使う。
→ `bool` 用の実装は `int` 用より後に登録すること（Python が自動で MRO を考慮）。

実際には Python の `singledispatch` は MRO を考慮して最も具体的な型を選ぶため、
`bool` → `int` → `object` の順で登録した場合、`True` に対しては `bool` 実装が選ばれる。

### O4: `functools.reduce` は空リストで `TypeError` — 初期値またはガードが必要

```python
functools.reduce(lambda acc, x: acc + x, [])  # TypeError: reduce() of empty iterable with no initial value
functools.reduce(lambda acc, x: acc + x, [], 0)  # 0 (初期値あり)
```

初期値なしの `reduce` は空リストで例外を raise する。
`sum()` のほうがシンプルだが、`reduce` は任意の二項演算に使えるため汎用性が高い。

## まとめ

FT129 は摩擦ゼロ確認。`functools` の各関数を FastAPI エンドポイントで活用する
パターンを確認した。特に `singledispatch` の `bool`/`int` 優先順位と、
`reduce` の空リストガードは実装時の注意点として記録する。
