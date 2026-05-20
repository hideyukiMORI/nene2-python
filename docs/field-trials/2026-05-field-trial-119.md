# Field Trial 119: functools.lru_cache / cache による関数レベルキャッシュ

## テーマ

`functools.cache`（maxsize=None）と `functools.lru_cache(maxsize=N)` を使って、
設定値・重い計算・外部ルックアップ結果をインプロセスでキャッシュするパターンを検証する。
`nene2.cache.TtlCache`（クラスベース・TTL付き）との使い分けも確認する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft119-lru-cache/` に以下を実装:

- `get_tax_rate()` — `@functools.cache` で国コード → 税率をキャッシュ（無制限）
- `calculate_discount_tier()` — `@functools.lru_cache(maxsize=128)` で金額 → 割引ティアをキャッシュ
- `cache_info()` / `cache_clear()` — キャッシュ統計・クリアの活用
- 13 テスト通過

## テスト結果

全 13 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `functools.cache` は maxsize=None の LRU キャッシュ

```python
@functools.cache  # maxsize=None — 全結果を永続保持
def get_tax_rate(country_code: str) -> float:
    ...

get_tax_rate.cache_info()  # CacheInfo(hits=N, misses=M, maxsize=None, currsize=K)
get_tax_rate.cache_clear()
```

`@functools.cache` は Python 3.9+ で追加された `@functools.lru_cache(maxsize=None)` の省略形。
メモリが許す限り全結果を保持する。不変データ・有限キー空間の関数に適切。

### O2: `cache_info()` でキャッシュ効率を計測できる

```python
info = get_tax_rate.cache_info()
# CacheInfo(hits=3, misses=2, maxsize=None, currsize=2)
print(f"hit率: {info.hits / (info.hits + info.misses):.1%}")
```

テストで `hits >= 1` を確認することで、キャッシュが実際に効いていることを保証できる。

### O3: `TtlCache` vs `lru_cache` の使い分け

| 特性 | `functools.lru_cache` | `nene2.cache.TtlCache` |
|---|---|---|
| TTL | なし（永続） | あり（秒単位） |
| キー | 関数引数のタプル | 任意の文字列 |
| 最大サイズ | `maxsize` で制限 | 制限なし |
| invalidation | `cache_clear()` または LRU 追い出し | TTL 期限切れ |
| 用途 | 純粋関数・不変データ | 外部API・DB クエリ結果 |

時間依存データ（株価・在庫）は `TtlCache`、数学計算・設定値は `lru_cache` が適切。

## まとめ

FT119 は摩擦ゼロ確認。`functools.cache` / `lru_cache` は純粋関数の結果キャッシュに最適。
TTL が必要な場合は `nene2.cache.TtlCache` と使い分けることで適切なキャッシュ戦略を選択できる。
