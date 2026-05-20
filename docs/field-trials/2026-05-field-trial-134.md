# Field Trial 134: typing モジュールの高度な活用

## テーマ

`ParamSpec`, `Concatenate`, `TypeGuard`, `Never`, Python 3.12 の `type` エイリアス構文を使った
高度な型アノテーションを FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft134-typing-advanced/` に以下を実装:

- `type UserId = int` — Python 3.12 の `type` エイリアス構文
- `type Handler[T] = Callable[[T], JsonDict]` — ジェネリックな型エイリアス
- `ParamSpec` + `Concatenate` — `request_id` 引数を自動注入するデコレーター
- `TypeGuard[Email]` / `TypeGuard[int]` — 型の絞り込み
- `Never` + `assert_never()` — 到達不能コードの型安全な表現
- `GET /users/{id}` — ParamSpec で request_id 自動注入
- `GET /validate` — TypeGuard で入力を分類
- 23 テスト通過

## テスト結果

全 23 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: Python 3.12 の `type` エイリアス構文でエイリアスが明示的になった

```python
type UserId = int
type Email = str
type JsonDict = dict[str, object]
type Handler[T] = Callable[[T], JsonDict]  # ジェネリックも使える
```

旧 `UserId = int`（変数代入）と異なり、`type` キーワードで型エイリアスとして明示される。
mypy/pyright がエイリアスとして認識し、より正確な型チェックが可能。

### O2: `ParamSpec` + `Concatenate` でデコレーターの引数を型安全に注入できる

```python
P = ParamSpec("P")

def with_request_id(
    func: Callable[Concatenate[str, P], JsonDict],
) -> Callable[P, JsonDict]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> JsonDict:
        return func(str(uuid.uuid4()), *args, **kwargs)
    return wrapper

@with_request_id
def fetch_user(request_id: str, user_id: UserId) -> JsonDict: ...

fetch_user(1)  # OK: request_id は自動注入
fetch_user("ignored", 1)  # TypeError: 型システムが extra arg を検出
```

`Concatenate[str, P]` で「最初の引数が str で残りが P」を表現できる。
デコレーターで引数を追加・削除するパターンの型安全な実装に不可欠。

### O3: `TypeGuard` で型の絞り込みが型システムに伝わる

```python
def is_valid_email(value: object) -> TypeGuard[Email]:
    return isinstance(value, str) and "@" in value and len(value) >= 5

if is_valid_email(value):
    # value: Email (str) として mypy が認識
    print(value.split("@")[1])  # OK
```

通常の `isinstance` チェックで対応できない複合条件（str かつ @ を含む）を
型ガード関数として定義できる。

### O4: `bool` は `int` のサブクラス — `is_positive_int(True)` は `True`

```python
def is_positive_int(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and value > 0

is_positive_int(True)   # True (True == 1 > 0)
is_positive_int(False)  # False (False == 0, not > 0)
```

`bool` は Python で `int` のサブクラスなので、`isinstance(True, int)` は `True`。
`bool` を除外したい場合は `isinstance(value, int) and not isinstance(value, bool)` が必要。

## まとめ

FT134 は摩擦ゼロ確認。`ParamSpec` + `Concatenate` によるデコレーター型安全化と
`TypeGuard` による型絞り込みを FastAPI エンドポイントで確認した。
Python 3.12 の `type` エイリアス構文も `TypeVar` なしでジェネリックエイリアスが書けることを確認。
