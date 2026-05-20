# Field Trial 143: inspect モジュール

## テーマ

`inspect.signature`, `inspect.getmembers`, `inspect.is*`, `inspect.currentframe`,
`inspect.iscoroutinefunction` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft143-inspect/` に以下を実装:

- `get_signature_info()` — 関数のパラメーター名・デフォルト値・型注釈を取得
- `has_required_params()` — 関数に必須パラメーターが存在するか確認
- `get_class_methods()` — クラスの公開メソッド一覧（`inspect.getmembers + isfunction`）
- `get_class_properties()` — クラスの `@property` 一覧
- `classify_object()` — `inspect.is*` でオブジェクトの種類を分類
- `get_caller_name()` — `inspect.currentframe` で呼び出し元の関数名取得
- `get_call_stack_depth()` — `inspect.stack` でコールスタックの深さ取得
- 28 テスト通過（摩擦1件あり）

## テスト結果

初回: 2失敗 → 修正後: 28テスト全通過。

## Friction Points

### FP1: `inspect.isfunction()` は async 関数にも True を返す

```python
async def my_async_func() -> int:
    return 1

inspect.isfunction(my_async_func)       # → True (!)
inspect.iscoroutinefunction(my_async_func)  # → True
```

`classify_object` で `isfunction` を先にチェックしたため、
async 関数が `"function"` に分類されて `"coroutine_function"` にならなかった。

**対処**: `iscoroutinefunction` を `isfunction` より先にチェックするよう順序を変更した。
async 関数は両方の述語に対して True を返すため、より具体的な述語を先に評価する。

## 観察

### O1: `inspect.signature` でパラメーターの種類を `kind.name` で取得できる

```python
sig = inspect.signature(func)
for name, param in sig.parameters.items():
    print(param.kind.name)  # POSITIONAL_OR_KEYWORD, KEYWORD_ONLY, VAR_POSITIONAL, etc.
```

`def f(x, y=10, *, z="hello")` の場合:
- `x`: `POSITIONAL_OR_KEYWORD`
- `y`: `POSITIONAL_OR_KEYWORD`（デフォルトあり）
- `z`: `KEYWORD_ONLY`（`*` の後ろ）

### O2: `inspect.Parameter.empty` はデフォルト値・型注釈の「未設定」を示すシングルトン

```python
if param.default is inspect.Parameter.empty:
    # デフォルト値なし（必須パラメーター）
    ...

if param.annotation is inspect.Parameter.empty:
    # 型注釈なし
    ...
```

`None` と区別するために専用のシングルトン `inspect.Parameter.empty` を使う。

### O3: `inspect.getmembers(cls, predicate=inspect.isfunction)` でメソッドのみ取得できる

```python
methods = [
    name
    for name, value in inspect.getmembers(cls, predicate=inspect.isfunction)
    if not name.startswith("_")
]
```

`predicate` 引数でフィルタリングできる。プロパティは `isfunction` では取得できず、
`isinstance(value, property)` で別途確認する必要がある。

### O4: `inspect.currentframe()` で呼び出し元の情報が取得できる

```python
frame = inspect.currentframe()
caller = frame.f_back.f_code.co_name  # 呼び出し元の関数名
```

デバッグ・ロギング・開発ツール向け。本番コードでの過度な使用は非推奨
（パフォーマンスへの影響がある）。

### O5: `inspect.iscoroutinefunction` は async def を検出する

```python
async def fetch() -> None: ...
def regular() -> None: ...

inspect.iscoroutinefunction(fetch)    # True
inspect.iscoroutinefunction(regular)  # False
inspect.isfunction(fetch)             # True（!）— async も isfunction は True
inspect.isfunction(regular)           # True
```

FastAPI の `@app.get` でも非同期ハンドラーと同期ハンドラーを区別する際に使われる。

## まとめ

FT143 は摩擦1件（`inspect.isfunction` が async 関数にも True を返す — チェック順序が重要）。
`inspect.signature` による関数シグネチャ解析と `inspect.getmembers` による
クラスイントロスペクションを FastAPI で確認した。
