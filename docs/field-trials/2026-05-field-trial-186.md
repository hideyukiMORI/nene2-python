# FT186: functools

**日付**: 2026-05-21
**テーマ**: functools モジュール — キャッシュ・部分適用・デコレーター・比較・ディスパッチ
**セキュリティ診断**: あり（186 % 3 = 0）
**クラッカーペンテスト**: なし（186 % 4 = 2）

---

## 概要

Python 標準ライブラリ `functools` は高階関数・関数オブジェクトのユーティリティ集である。
`lru_cache`・`cache`（メモ化）、`partial`（部分適用）、`reduce`（畳み込み）、`wraps`（デコレーターメタデータ保持）、`total_ordering`（比較演算子補完）、`singledispatch`（型ディスパッチ）、`cached_property`（インスタンスレベルキャッシュ）を検証した。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft186-functools/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `fibonacci(n)` | `lru_cache` でメモ化したフィボナッチ数列 |
| `fibonacci_safe(n)` | 上限チェック付きフィボナッチ（DoS 対策）|
| `get_fibonacci_cache_stats()` | キャッシュ統計取得 |
| `factorial(n)` | `functools.cache` で無制限メモ化した階乗 |
| `power(base, exponent)` / `square` / `cube` | `partial` で指数固定関数 |
| `make_multiplier(factor)` | `partial` で乗数固定の乗算関数を生成 |
| `product(numbers)` | `reduce` でリストの積 |
| `flatten_once(nested)` | `reduce` で1段階展開 |
| `timing_decorator(func)` | `@wraps` でメタデータ保持するタイミングデコレーター |
| `retry(max_attempts)` | `@wraps` を使ったリトライデコレーターファクトリ |
| `Version` | `@total_ordering` + `dataclass` でセマンティックバージョン比較 |
| `latest_version(versions)` | `reduce` + `Version` で最新バージョン検出 |
| `serialize(value)` | `singledispatch` で型別シリアライズ |
| `DataProcessor` | `cached_property` でコストの高い計算をキャッシュ |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/fibonacci` | lru_cache フィボナッチ |
| POST | `/factorial` | cache 階乗 |
| POST | `/power` | partial square/cube |
| POST | `/multiply` | partial 乗算 |
| POST | `/product` | reduce 積 |
| POST | `/flatten` | reduce 展開 |
| POST | `/version/latest` | total_ordering + reduce 最新バージョン |
| POST | `/serialize` | singledispatch シリアライズ |
| POST | `/stats` | cached_property 統計 |

---

## テスト結果

**64 passed**

```
64 passed in 0.36s
```

mypy --strict: Success  
ruff check: All checks passed  
pip-audit: PYSEC-2025-183 (PyJWT via mcp transitive dep — 許容済み)

---

## 摩擦ポイント

### F-1: `base**exponent` の戻り値型が `Any`（mypy --strict）（深刻度: 低）

**事象**: `return base**exponent` をそのまま返すと `Returning Any from function declared to return "float"` エラー。Python の `**` 演算子は型に応じて `int | float | complex` を返すため、mypy が型推論できない。

**原因**: `float ** float` の演算子オーバーロードが `float` ではなく `Any` として型付けされている（typeshed の制約）。

**対応**: `return float(base**exponent)` と明示的にキャストすることで解決。

---

## 観察点

### 観察1: `lru_cache` の `maxsize` と DoS 対策

```python
@functools.lru_cache(maxsize=256)
def fibonacci(n: int) -> int:
    ...

def fibonacci_safe(n: int) -> int:
    if n > 90:
        raise ValueError(...)
    return fibonacci(n)
```

`lru_cache` は入力値ごとにキャッシュエントリを作成する。`maxsize=None`（= `functools.cache`）の場合、引数のバリエーションが多い用途では無制限にメモリを使い続ける可能性がある。入力値を `fibonacci_safe` でサニタイズしてから `lru_cache` 付き関数を呼ぶことで、キャッシュの肥大化を防ぐ。

### 観察2: `functools.cache` vs `lru_cache(maxsize=None)`

```python
@functools.cache        # Python 3.9+
def factorial(n: int) -> int: ...

@functools.lru_cache(maxsize=None)  # Python 3.2+
def factorial(n: int) -> int: ...
```

`functools.cache` は `lru_cache(maxsize=None)` の簡易エイリアスで、`cache_info()` / `cache_clear()` メソッドを持つ点は同じ。`lru_cache` より書きやすく、上限なしキャッシュが明示的。

### 観察3: `@wraps` なしでメタデータが失われる問題

```python
# wraps なし — name が "wrapper" になる
def bad_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

# wraps あり — name が元の関数名を保持
def good_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

`@wraps` を省くと `__name__`・`__doc__`・`__annotations__` が全てラッパーのものに置き換わる。pytest の `--tb=short` でも関数名が `wrapper` と表示され、デバッグが困難になる。

### 観察4: `total_ordering` と `frozen=True` の組み合わせ

`@functools.total_ordering` と `@dataclass(frozen=True)` を組み合わせる場合、`@dataclass(eq=False)` を指定しないと `dataclass` が自動生成する `__eq__` が `total_ordering` の `__eq__` を上書きしてしまう可能性がある。今回は `__eq__` と `__lt__` を明示的に実装したため問題なし。

### 観察5: `singledispatch` と `bool` 型のディスパッチ順序

```python
@serialize.register(bool)
def _serialize_bool(value: bool) -> str: ...

@serialize.register(int)
def _serialize_int(value: int) -> str: ...
```

Python では `bool` は `int` のサブクラス。`@register(int)` を先に登録すると `True`/`False` も `int` ハンドラーで処理される。`bool` を意図的に分岐させたい場合は `@register(bool)` を先（または明示的に）登録する必要がある。

---

## セキュリティ診断（FT186 % 3 = 0）

### 1. OWASP API Security Top 10 (2023)

#### API6: Unrestricted Access to Sensitive Business Flows — DoS via lru_cache

**状況**: `fibonacci(n)` に上限なく大きな `n` を渡せた場合、計算時間 + キャッシュメモリの両面で DoS が成立する。

**対策**: `fibonacci_safe(n)` が Pydantic の `le=90` と合わせて二重に入力を制限している。FastAPI の `Field(ge=0, le=90)` による検証は HTTP 境界で確実に発動する。**問題なし**。

#### API4: Unrestricted Resource Consumption

**状況**: `/stats` エンドポイントは `list[int]` を最大 1000 要素受け取る。`cached_property` はインスタンスごとにキャッシュするため、毎リクエストで新たな `DataProcessor` インスタンスが生成され、キャッシュは1リクエスト内のみで有効。メモリは GC に依存するが、1000 要素程度ならリスクは低い。**問題なし**。

**状況**: `/flatten` は `list[list[int]]` を最大 50 要素受け取り `reduce` で結合するが、内側リストの要素数に上限がない。理論上、巨大な内側リストを送れる。

**判定**: **MEDIUM** — 内側リストに個別の `max_length` が設定されていない（F-2 として記録）。

### 2. インジェクション攻撃

`functools` API は外部入力を直接評価する機能を持たないため、インジェクションリスクはない。`singledispatch` の型ルーティングも実行コードを動的生成しない。**問題なし**。

### 3. 認証・認可

今回のエンドポイントは認証不要の計算 API のため対象外。**問題なし**。

### 4. 入力バリデーション

| フィールド | 制約 | 評価 |
|---|---|---|
| `FibRequest.n` | `ge=0, le=90` | ✅ |
| `FactorialRequest.n` | `ge=0, le=20` | ✅ |
| `PowerRequest.operation` | `max_length=10` | ✅ |
| `ProductRequest.numbers` | `max_length=100` | ✅ |
| `FlattenRequest.nested` | `max_length=50` (外側のみ) | ⚠️ 内側なし |
| `VersionRequest.versions` | `max_length=50` | ✅ |
| `StatsRequest.data` | `max_length=1000` | ✅ |

### 5. 情報漏洩

`retry` デコレーターがリトライ失敗時に元の例外を `raise` するため、内部エラーメッセージがそのまま上位に伝播する。FastAPI の `ErrorHandlerMiddleware` がない場合、500 レスポンスに内部エラーが含まれる可能性がある。FT のサンドボックスでは許容範囲内。**問題なし**（本番実装では `ErrorHandlerMiddleware` を追加すること）。

pip-audit: PYSEC-2025-183 (PyJWT via mcp — 許容済み、修正版待ち)

### 6. Python/FastAPI 固有

#### ReDoS

`Version.parse()` は `.split(".")` と `int()` のみを使用。正規表現を使用しないため ReDoS リスクなし。**問題なし**。

#### functools.cache の無制限メモリ使用

`factorial` は `functools.cache`（無制限）を使用しているが、`FactorialRequest.n` が `le=20` で制限されているため、キャッシュエントリは最大 21 個。**問題なし**。

#### singledispatch の型安全性

`singledispatch` は実行時型チェックを行うため、Pydantic で検証済みの型が渡される限り不正ディスパッチは発生しない。**問題なし**。

### セキュリティ診断まとめ

| カテゴリ | 結果 | 備考 |
|---|---|---|
| OWASP API Top 10 | 条件付き合格 | F-2 /flatten 内側リスト上限なし |
| インジェクション | 合格 | |
| 認証・認可 | 対象外 | |
| 入力バリデーション | 条件付き合格 | F-2 参照 |
| 情報漏洩 | 合格 | ErrorHandlerMiddleware 推奨 |
| Python/FastAPI 固有 | 合格 | |

**診断結果: 条件付き合格**（MEDIUM 1件 — 次 FT までに修正推奨）

---

## Follow-up Issues

### F-2: `/flatten` 内側リストの要素数に上限なし（深刻度: MEDIUM）

**事象**: `FlattenRequest.nested: list[list[int]]` の外側は `max_length=50` で制限されているが、内側リストの要素数に上限がない。悪意のある入力で内側に大量要素を持つリストを送ることができる。

**対応**: Pydantic の `Annotated[list[int], Field(max_length=1000)]` を使って内側リストにも上限を設定する。

---

## DX Review — 6ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「関数をキャッシュする」という概念が `@lru_cache` によって視覚的に分かりやすく表現されている。デコレーター1行で劇的に高速化できる体験は印象的。

**ドキュメント理解**: `partial` の「引数を固定した新しい関数を作る」という概念は直感的。しかし `reduce` の「畳み込み」は初見では理解しにくく、`sum()` や `max()` で代替できる場合が多い旨を添えた方が親切。

**事故リスク**: 低 — ただし `lru_cache(maxsize=None)` は上限なしキャッシュであることを知らないと、長時間稼働するプロセスでメモリが肥大化するリスクがある（サンドボックスでは `fibonacci_safe` で回避済み）。

**規約の使いやすさ**: `@wraps` の必要性（デバッグ時の関数名保持）を理解するまでは省略しがち。テストで `__name__` を確認するパターンを見ることで習得できる。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`lru_cache` のコピペ利用は頻繁。`maxsize` を適切に設定することを忘れがちで、`None` のまま運用してメモリリークを引き起こすケースがある。

**コピペ可能性**: `timing_decorator` と `retry` はそのまま転用できるユーティリティとして高い実用性。

**拡張時の罠**: `total_ordering` + `dataclass(frozen=True)` の組み合わせで `__eq__` を省略するとデフォルトの `dataclass` が生成した `__eq__` が使われ、`total_ordering` の期待と異なる場合がある（観察4参照）。

**事故リスク**: 中（lru_cache の maxsize 設定忘れ）

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `useMemo` / `useCallback` に近い概念として `lru_cache` / `partial` を理解できる。`singledispatch` は TypeScript のオーバーロードと比べてコードが分散するが、`@register` で後から拡張できる点は優れている。

**エラーレスポンスの質**: `/version/latest` の `400 Bad Request` + `detail` に無効バージョン文字列を含めるのは適切。

**Python 固有概念の学習コスト**: `reduce` は TS では `Array.prototype.reduce` があるので理解しやすいが、Python 3 での `reduce` の立ち位置（`functools.reduce` に格下げされた経緯）を知ると設計哲学が掴める。

**事故リスク**: 低

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`cached_property` は Django モデルの `@property` + 手動キャッシュより洗練されている。リクエストごとに新インスタンスを作成するケースでは「1リクエスト内のみ有効なキャッシュ」として機能するため、副作用なく使いやすい。

**他フレームワークとの差異**: Django の `django.utils.functional.cached_property` は非スレッドセーフだが、`functools.cached_property` も非スレッドセーフ（Python 3.12 以前）。スレッドセーフが必要な場合は明示的なロックが必要。

**nene2 の薄さへの評価**: `functools` は nene2 フレームワークと独立しているため、どの FastAPI プロジェクトでも直接適用できる内容として評価が高い。

**事故リスク**: 低

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `lru_cache` の `maxsize` が適切か（サービスの想定入力範囲に合っているか）
- `cache`（無制限）を使う場合、入力バリエーションが有限であることが保証されているか
- `@wraps` が全てのデコレーター実装に付いているか
- `singledispatch` のデフォルト実装が意図した型を処理するか（意図しない型が来たときの挙動）
- `total_ordering` で `__eq__` と `__lt__` の両方が実装されているか

**チームでの安全なパターン**: `retry` デコレーターはチーム共有のユーティリティとして使えるが、リトライ間隔（`sleep`）・バックオフ・特定例外のみリトライなど実装が必要な場合は `tenacity` ライブラリの使用を推奨する。

**事故リスク**: 低

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**:
- `dataclass(frozen=True, slots=True)`: `CacheStats` / `Version` で適用済み ✅
- Pydantic は HTTP 境界のみ: `app.py` の Request/Response モデルのみ ✅
- `create_app()` はファイル末尾: 適用済み ✅
- `max_length` 指定: 外側リストには設定済み（F-2: 内側リスト未設定）⚠️
- セキュリティ診断実施: FT186 % 3 = 0 → 診断実施 ✅

**初心者でも安全な API 達成度**: `fibonacci_safe` による DoS 防御ラッパーパターン（上限チェック → メモ化関数呼び出し）は安全なキャッシュ利用の模範として機能している。Pydantic の `le=` と `fibonacci_safe` の両方で二重バリデーションしている点も good practice。

---

*バージョン: v1.8.57*
