# Field Trial 128: itertools モジュールの高度な活用

## テーマ

`chain`, `islice`, `groupby`, `product`, `combinations`, `accumulate` を使った
データ処理・組み合わせ生成・累積集計を FastAPI エンドポイントで検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft128-itertools/` に以下を実装:

- `paginate_iter()` — `islice` を使ったページネーション
- `group_sales_by_region()` — `groupby` を使ったリージョン別グルーピング
- `running_total()` — `accumulate` を使った累積合計
- `merge_datasources()` — `chain` を使った複数ソースのマージ
- `GET /sales` — islice によるページネーション
- `GET /sales/by-region` — groupby によるリージョン別集計
- `GET /sales/running-total` — accumulate による累積合計
- `GET /combinations/regions` — combinations によるリージョン組み合わせ
- `GET /product/region-month` — product によるデカルト積
- `GET /sales/merged` — chain による複数ソースマージ
- 15 テスト通過

## テスト結果

全 15 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `groupby` は事前ソートが必要

```python
sorted_sales = sorted(sales, key=lambda s: s.region)
grouped = {
    region: list(group)
    for region, group in itertools.groupby(sorted_sales, key=lambda s: s.region)
}
```

`itertools.groupby` はキーが連続している要素のみをグループにまとめる。
事前ソートなしだと同じキーが分散してしまう。SQL の `GROUP BY` とは挙動が異なる。

### O2: `islice` でイテレーター対応のページネーションが書ける

```python
def paginate_iter[T](iterable: list[T], page: int, per_page: int) -> list[T]:
    start = (page - 1) * per_page
    return list(itertools.islice(iter(iterable), start, start + per_page))
```

`list[start:end]` スライスより `islice` のほうがジェネレーターにも適用できる。
ただし `islice` はランダムアクセスではなく先頭から順に読み進めるため、
大きなオフセットでも O(n) になる点は注意。

### O3: `accumulate` で累積集計がシンプルに書ける

```python
monthly_amounts = [100, 200, 150]
cumulative = list(itertools.accumulate(monthly_amounts))
# → [100, 300, 450]
```

デフォルト演算子は加算。`operator.mul` などを渡せば積の累積にもなる。

### O4: `combinations` と `product` でデータの組み合わせを生成できる

```python
regions = ["east", "north", "south"]
# 2つ選ぶ組み合わせ (順序なし): 3C2 = 3通り
combos = list(itertools.combinations(regions, 2))

# デカルト積 (すべての組み合わせ): 3×3 = 9通り
pairs = list(itertools.product(regions, months))
```

API のテストデータ生成や「全ペア比較」パターンに便利。

## まとめ

FT128 は摩擦ゼロ確認。`itertools` の各関数を FastAPI エンドポイントで活用する
パターンを確認した。特に `groupby` の事前ソート要件は見落としやすいポイント。
