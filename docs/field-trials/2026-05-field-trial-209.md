# FT209: functools モジュール — partial / lru_cache / reduce / wraps

**日付**: 2026-05-22
**テーマ**: Python `functools` モジュールの partial / lru_cache / reduce / wraps の実装と検証
**セキュリティ診断**: なし（209 % 3 = 2）
**クラッカーペンテスト**: なし（209 % 4 = 1）

---

## 概要

`functools` モジュールは Python 標準ライブラリの高階関数・デコレータユーティリティ。
今 FT では以下の 4 機能を HTTP API として実装した。

| 関数/デコレータ | ユースケース |
|---|---|
| `partial` | 引数の部分適用（固定指数の累乗関数） |
| `lru_cache` | 再帰関数のメモ化（フィボナッチ数列） |
| `reduce` | シーケンスの逐次集約（sum / product / max / min） |
| `wraps` | デコレータのメタデータ保持（関数名・docstring） |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft209-functools/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `apply_partial_power(exponent, bases)` | `partial(_power, exponent=N)` で累乗関数を部分適用 |
| `compute_fibonacci(n)` | `@lru_cache` 付き再帰フィボナッチ数とキャッシュ情報 |
| `reduce_numbers(numbers, operation)` | `reduce` で sum / product / max / min 集約 |
| `slow_sum(numbers)` | `@timed`（`@wraps` 内包）で実行時間計測付き合計 |
| `inspect_wrapped_function()` | `@wraps` が関数名・docstring を保持することを確認 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/functools/partial-power` | 部分適用累乗 |
| GET | `/functools/fibonacci/{n}` | lru_cache メモ化フィボナッチ数 |
| POST | `/functools/reduce` | 逐次集約 |
| POST | `/functools/timed-sum` | @wraps 付き実行時間計測 |
| GET | `/functools/wraps-info` | @wraps メタデータ確認 |

---

## テスト結果

**22 passed**

```
22 passed in 0.38s
```

---

## 摩擦ポイント

### F-1: `@wraps` デコレータの戻り値型と mypy の挙動（Python 3.14）

`timed` デコレータで `wrapper` の戻り値が `TimedResult` であるため、
`Callable[..., T]` を返す関数として宣言した場合に型不一致が起きる。

Python 3.14 の mypy では `# type: ignore[return-value]` が「不要」として警告された。
`@functools.wraps(func)` が型情報を適切に伝播するため、
Python 3.14 以降では型無視コメントが不要になっている。

```python
# Python 3.14: type: ignore 不要
def timed[T](func: Callable[..., T]) -> Callable[..., TimedResult]:
    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> TimedResult:
        ...
    return wrapper  # Python 3.14 では ignore なしで通る
```

また、`*args: Any` と `**kwargs: Any` は ruff の ANN401 ルールで禁止されるため、
`*args: object, **kwargs: object` を使う必要がある。

---

## 観察点

### 観察1: `partial` はキーワード引数のみ固定できる（位置引数は前から）

```python
from functools import partial

def _power(base: float, exponent: float) -> float:
    return base ** exponent

# キーワード引数で固定
square = partial(_power, exponent=2.0)
square(base=3.0)  # → 9.0

# 位置引数で固定（先頭から）
power_of_3 = partial(_power, 3.0)  # base=3.0 を固定
power_of_3(2.0)  # → 9.0（3^2）
```

`partial` はキーワード引数で特定の引数を固定できる。
固定した引数は呼び出し時に指定しなくてよい。
ファクトリ関数パターン（同じ設定のバリアント生成）に有用。

### 観察2: `lru_cache` はモジュールレベルで一度だけ生成する

```python
@functools.lru_cache(maxsize=128)
def _fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return _fibonacci(n - 1) + _fibonacci(n - 2)
```

`@lru_cache` はモジュールレベルの関数に適用することで永続キャッシュになる。
HTTP リクエストごとにキャッシュをリセットしたい場合は `cache_clear()` を呼ぶ。
今 FT では「リクエストごとにリセットして hits/misses を正確に返す」設計を採用した。

`fib(50)` = 12,586,269,025 を計算しても 51 回の再帰（misses=51）だけで済む（メモ化なしは 2^50 回）。

### 観察3: `reduce` は初期値あり・なしで挙動が異なる

```python
from functools import reduce

# 初期値なし（リストが空だと TypeError）
reduce(lambda acc, x: acc + x, [1, 2, 3])        # → 6
reduce(lambda acc, x: acc + x, [])               # → TypeError!

# 初期値あり（空リストでも安全）
reduce(lambda acc, x: acc + x, [], 0)            # → 0
reduce(lambda acc, x: acc * x, [1, 2, 3], 1.0)  # → 6.0（float として計算）
```

`reduce` の第 3 引数（初期値）は空リスト対策として必ず設定すること。
`sum` / `product` は初期値 `0.0` / `1.0` で安全。
`max` / `min` は初期値を設定すると意味が変わるため、空リストは Pydantic の `min_length=1` で防御。

### 観察4: `@wraps` がないと `__name__` / `__doc__` が消える

```python
import functools

def without_wraps(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def with_wraps(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@without_wraps
def my_func():
    """My docstring."""
    pass

@with_wraps
def my_func2():
    """My docstring."""
    pass

my_func.__name__   # → "wrapper"（元の名前が消える！）
my_func2.__name__  # → "my_func2"（@wraps で保持）
my_func2.__wrapped__  # → 元の関数にアクセス可能
```

`@wraps` を使わないと `__name__`・`__doc__`・`__module__` が `wrapper` のものに上書きされる。
デバッグ・ログ・API ドキュメント生成（FastAPI の OpenAPI）に悪影響が出る。

---

## nene2-python フレームワークとの統合

- `@lru_cache` は HTTP ハンドラーに直接適用しない。UseCase / ドメイン層の純粋関数に適用する。
  ハンドラーはリクエストごとに新しいインスタンスが生成されるため、キャッシュが共有されない。
- `reduce` の初期値は必ず指定する。空リストは Pydantic `min_length=1` で防御する。
- デコレータを作る場合は必ず `@functools.wraps` を使う（FastAPI の OpenAPI 生成への影響を防ぐ）。
- `*args: object, **kwargs: object` を使う（`Any` は ruff ANN401 で禁止）。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`partial` を使って「設定済み API クライアント」を作ろうとしている。

**ドキュメント理解**: `partial(func, arg1, arg2)` の順序（位置引数は前から固定）は混乱しやすい。
キーワード引数 `partial(func, param=value)` の方が意図が明確。  
**事故リスク**: 低。`partial` 自体は安全。初期値なし `reduce` の TypeError は `min_length=1` で防御済み。  
**規約の使いやすさ**: `partial` より `lambda` の方が初心者には読みやすい場合もある。
チームの熟練度に合わせて使い分ける。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`@lru_cache` でパフォーマンスを改善しようとしている。

**コピペ可能性**: `@functools.lru_cache(maxsize=128)` は 1 行で追加できる。コピペしやすい。  
**拡張時の罠**: `@lru_cache` を適用した関数の引数は **ハッシュ可能** でなければならない。
`list` や `dict` を引数に持つ関数には使えない（`TypeError` が出る）。  
**セキュリティ的な事故リスク**: 中。`@lru_cache` を使うと引数の値がキャッシュに残る。
パスワード・トークンなどを引数に渡す関数に適用すると情報が残留する。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS の `useMemo` / `useCallback` から Python の `lru_cache` / `partial` に移行しようとしている。

**エラーレスポンスの質**: `422 + n_out_of_range` は明確。  
**Python 固有概念の学習コスト**: `@lru_cache` は React の `useMemo` に近い。
`partial` は JS の `Function.prototype.bind(this, arg1)` に相当するが、
`this` バインディングがないため理解しやすい。  
**事故リスク**: 低。TypeScript 的な型安全さは mypy strict で担保される。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

マスターデータのキャッシュ戦略を設計しようとしている。

**他フレームワークとの差異**: Django の `@cache_page` / `@cached_property` とは対象が異なる。
`@lru_cache` は純粋関数のメモ化に特化。HTTP レスポンスキャッシュには別の仕組みが必要。  
**nene2-python の薄さへの評価**: `@lru_cache` を UseCase 層に使うのは自然。
ただし `cache_clear()` のタイミング（キャッシュ無効化）を設計に組み込む必要がある。  
**本番投入可能性**: `@lru_cache` + `maxsize=128` + `cache_clear()` on mutation は本番投入可能。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

コードレビューで `functools` の使用箇所を確認しようとしている。

**コードレビューチェックポイント**:
- [ ] `@lru_cache` の引数が全てハッシュ可能か（`list` / `dict` を持つと RuntimeError）
- [ ] `@lru_cache` の引数に機密情報（パスワード・トークン）が含まれないか
- [ ] `reduce` に初期値が設定されているか（空リストで TypeError にならないか）
- [ ] カスタムデコレータに `@functools.wraps` があるか（FastAPI OpenAPI への影響）
- [ ] `partial` の引数固定順序が意図通りか（位置引数は前から固定される）

**チームでの安全なパターン**:
1. `@lru_cache` は UseCase / ドメイン層の純粋関数に限定
2. `reduce` は初期値必須をコーディング規約に追加
3. デコレータ作成時は `@functools.wraps` 必須を規約化

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高。`*args: object` でANN401回避・`@wraps` 必須を実証。  
**「初心者でも安全な API」達成度**: 高。`min_length=1` で空リスト防御済み。  
**設計上の負債**: なし。  
**Follow-up Issue 候補**: なし

---

## Follow-up Issues

なし（今 FT 内で全問題を解決）

---

## まとめ

`functools` の 4 機能はいずれも実用的で、nene2-python の HTTP API 層に自然に統合できた。

最大の学習ポイントは:
1. **`@lru_cache` の引数はハッシュ可能でなければならない** — `list` / `dict` は使えない
2. **`reduce` の初期値は必ず設定する** — 空リストで `TypeError` になる
3. **`@wraps` なしのデコレータは `__name__` を破壊する** — FastAPI の OpenAPI にも影響
4. **`*args: object` を使う** — `Any` は ruff ANN401 で禁止
5. **Python 3.14 では `type: ignore` が不要になるケースがある** — `@wraps` の型推論が改善

次の FT210 は `210 % 3 = 0` → セキュリティ診断あり、`210 % 4 = 2` → クラッカーペンテストなし。
