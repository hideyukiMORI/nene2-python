# FT166: functools モジュール

**日付**: 2026-05-21
**テーマ**: `functools` モジュール — `lru_cache`・`cached_property`・`partial`・`wraps`・`reduce`・`cache`
**セキュリティ診断**: なし（166 % 3 = 1）

---

## 概要

Python 標準ライブラリの `functools` モジュールを nene2-python フレームワーク上で検証した。
`functools` は高階関数・デコレーター・メモ化のユーティリティを提供し、
nene2-python の DI パターン・レスポンスキャッシュ・ミドルウェア実装に直結する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft166-functools/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `fibonacci(n)` | `@lru_cache(maxsize=128)` でメモ化された再帰 fibonacci |
| `expensive_computation(key)` | `@lru_cache(maxsize=32)` で文字列キーのキャッシュ |
| `HeavyComputer` | `@cached_property` で total / average を遅延計算・キャッシュ |
| `double / triple` | `functools.partial` で multiply の引数を固定 |
| `greet_hello / greet_hi` | `partial` でテンプレートと記号を固定したあいさつ生成 |
| `timing_decorator` | `@functools.wraps` でデコレーターが元の関数名・docstring を保持 |
| `product_reduce(numbers)` | `functools.reduce` で積を計算 |
| `flatten_reduce(nested)` | `reduce` でネストしたリストをフラット化 |
| `collatz_steps(n)` | `@functools.cache`（unbounded）でコラッツ数列ステップ数をメモ化 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/functools/fibonacci` | lru_cache 付き fibonacci（キャッシュ統計返却） |
| GET | `/functools/lru-cache` | 任意キーのキャッシュ統計デモ |
| GET | `/functools/cached-property` | HeavyComputer の計算回数デモ |
| GET | `/functools/partial` | double / triple / greet デモ |
| GET | `/functools/wraps` | slow_add の __name__ 保持確認 |
| POST | `/functools/reduce-product` | 整数リストの積 |
| POST | `/functools/reduce-flatten` | ネストリストのフラット化 |
| GET | `/functools/cache-collatz` | unbounded cache でコラッツ数列 |

---

## テスト結果

**34 passed（摩擦ゼロ）**

```
34 passed in 0.83s
```

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

---

## 観察点

### 観察1: `@lru_cache` はグローバル状態 — テスト間でキャッシュを `clear` する必要がある

```python
@pytest.fixture(autouse=True)
def clear_caches() -> None:
    fibonacci.cache_clear()
    expensive_computation.cache_clear()
```

`@lru_cache` の対象関数はプロセス共有のキャッシュを持つ。
テスト間でキャッシュが汚染されるため `autouse=True` で毎回クリアする必要がある。
nene2-python でキャッシュを使う UseCase は `cache_clear()` を lifespan の shutdown で呼ぶか、
または `@lru_cache` をクラスメソッドに適用してインスタンス単位でスコープを制御する。

### 観察2: `@cached_property` はインスタンス単位 — `lru_cache` との使い分け

```python
class HeavyComputer:
    @functools.cached_property
    def total(self) -> int:
        self.compute_count += 1
        return sum(self._data)
```

`@cached_property` はインスタンスの `__dict__` に値を保存する。
同じインスタンスで 2 回目のアクセスは計算なし。新しいインスタンスは再計算。
`@lru_cache` はプロセス全体で共有・引数でキー管理、`@cached_property` はインスタンスで管理。
nene2-python での使い分け:
- UseCase / Repository インスタンスの設定値計算 → `@cached_property`
- 引数ベースの重い計算（ページネーション計算など）→ `@lru_cache`

### 観察3: `@functools.cache` = `@lru_cache(maxsize=None)` でメモリ無制限

```python
@functools.cache  # Python 3.9+ / unbounded
def collatz_steps(n: int) -> int: ...
```

`@cache` は `@lru_cache(maxsize=None)` の略記で、キャッシュサイズ制限なし。
再帰的な数学関数に適しているが、引数の値域が大きい場合はメモリ枯渇に注意。
nene2-python での用途: 設定値の解析結果など、引数の種類が少ない場合に使う。

### 観察4: `functools.partial` で DI 設定をカリー化できる

```python
double = functools.partial(multiply, y=2)
greet_hello = functools.partial(make_greeting, "Hello")
```

FastAPI の `Depends` と組み合わせる場合、`partial` でリポジトリに設定を注入できる:
```python
get_repo = functools.partial(NoteRepository, db_url=settings.db_url)
Depends(get_repo)
```
ただし `Depends` に渡す関数はシグネチャが重要なため、`partial` が残す引数を確認すること。

### 観察5: `@functools.wraps` なしのデコレーターは `__name__` を上書きする

```python
def timing_decorator(func):
    # @functools.wraps(func) がないと:
    def wrapper(*args, **kwargs): ...
    return wrapper  # → slow_add.__name__ == "wrapper" になる

def timing_decorator(func):
    @functools.wraps(func)  # ← これがないと OpenAPI ルート名が壊れる
    def wrapper(*args, **kwargs): ...
    return wrapper
```

FastAPI はルート関数の `__name__` を operationId に使う。
カスタムミドルウェア・デコレーターに `@functools.wraps` がないと OpenAPI スキーマが壊れる。

---

## nene2-python フレームワークとの統合

- `@lru_cache` は `TtlCache`（FT100 で追加済み）と役割が異なる（TTL なし vs TTL あり）
- `@cached_property` は Repository の設定パース結果のキャッシュに最適
- `@functools.wraps` は nene2-python の `BearerTokenMiddleware` 等のデコレーターで使用が推奨される
- `functools.reduce` は UseCase の集計ロジックに使えるが、`sum()` / リスト内包表記の方が可読性が高い場合が多い
- `@functools.cache` は設定値の解析・静的ルックアップに適している

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`@lru_cache` は「デコレーターをつけるとキャッシュされる」という概念は分かりやすいが、
`cache_clear()` が必要なことや、グローバル共有であることは見落としやすい。

**ドキュメント理解**: `@lru_cache` のサンプルはフィボナッチが定番だが、
「Web API の UseCase でいつ使うか」の例がないと「難しそうなやつ」で止まる。

**事故リスク**: 中。`@lru_cache` をテストで使うときにキャッシュをクリアし忘れ、
他のテストのキャッシュが漏れ込んでテストが通ったり失敗したりするフレーキーなテストが生まれる。

**規約の使いやすさ**: `@functools.wraps` の必要性は理解しにくい。
「デコレーターを作るときは必ず `@functools.wraps` をつける」という規則を覚えれば十分。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`functools` は名前を知っていても使いこなせていないことが多い。
`reduce` は「forループで書いた方が分かる」と言って使わない傾向がある。

**コピペ可能性**: `@lru_cache(maxsize=128)` と `@functools.wraps(func)` はそのままコピペできる。

**拡張時の罠**: `@lru_cache` の引数が変わったときにキャッシュが古い値を返し続ける。
引数の型が mutable（`list`, `dict`）だと `TypeError: unhashable type` が発生することに気づかない。

**セキュリティ的な事故リスク**: 低。ただし `@lru_cache` に認証情報を含む引数を渡すと
別ユーザーのキャッシュが混入するリスクがある（BOLA の一形態）。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`useMemo` / `useCallback` と `@lru_cache` / `@cached_property` は概念が近い。
「同じ入力なら再計算しない」という理解はすでにある。

**Python 固有概念の学習コスト**: `partial` は JS の `bind` や `curry` に近い概念。
`reduce` は `Array.prototype.reduce` と同じ。TypeScript ユーザーには直感的。

**事故リスク**: 低。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `@method_decorator` / `cache_page` との差異を理解している。
`@functools.wraps` は既知。`@lru_cache` の eviction ポリシー（LRU）を正確に理解している。

**他フレームワークとの差異**: Django は `cache.get/set` で明示的にキャッシュを管理する。
nene2-python で `@lru_cache` を使う場合、TTL がないことを意識する必要がある。
TTL が必要なら FT100 で追加した `TtlCache` を使う。

**本番投入可能性**: 問題なし。ただしキャッシュキーのサイズとメモリ消費量の設計が必要。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [ ] `@lru_cache` / `@cache` の引数に mutable 型（list, dict）が渡されていないか（`TypeError` になる）
- [ ] `@lru_cache` をリクエストスコープで使っていないか（プロセス共有で期待外の値が返る）
- [ ] `@lru_cache` に認証情報・ユーザーIDが引数に含まれる場合、BOLA にならないか
- [ ] デコレーターに `@functools.wraps` がついているか（OpenAPI operationId の破損防止）
- [ ] `@cache`（unbounded）を使う場合、引数の値域が有限か（メモリリーク防止）

**チームでの安全なパターン**: キャッシュが必要な UseCase は `cache_clear()` を公開メソッドとして持ち、
lifespan の shutdown / テストの teardown で明示的にクリアする規約を設ける。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高

**「初心者でも安全な API」達成度**: 中
- `@lru_cache` のキャッシュ汚染リスク（テスト・BOLA）をドキュメントが説明していない
- `@functools.wraps` の必要性が CLAUDE.md に明記されていない（FastAPI との相性問題）

**設計上の負債・ドキュメント不足**:
- nene2-python のカスタムデコレーター作成時の `@functools.wraps` 使用がポリシー化されていない
- `@lru_cache` の「リクエストスコープ不可・認証情報を引数に含めない」ルールが未文書

**Follow-up Issue 候補**: `docs: functools.wraps をカスタムデコレーター規約に追加`

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | `docs: @functools.wraps をデコレーター作成規約として CLAUDE.md に追加` | docs |
| 低 | `docs: @lru_cache のリクエストスコープ不可・認証情報禁止をキャッシュ how-to に記載` | docs |

---

## まとめ

`functools` は nene2-python の DI・キャッシュ・デコレーター実装に広く関連するモジュール。
34 テスト全通過、摩擦ゼロ。
`@cached_property` がインスタンス単位、`@lru_cache` がプロセス単位という使い分けが重要。
`@functools.wraps` なしのデコレーターは FastAPI の operationId を破壊するため、
カスタムデコレーター規約への追記が推奨される。
