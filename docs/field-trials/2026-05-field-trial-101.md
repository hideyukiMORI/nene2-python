# Field Trial 101: Query Parameter Filter/Sort パターン

## テーマ

`?status=published&sort=views&order=desc&tag=fastapi` のような複数フィルター + ソートのクエリパラメーターを型安全に扱うパターンを nene2 上で実装する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft101-query-filter/` に以下を実装:

- `ArticleFilter` dataclass に `StrEnum` で列挙型フィルター
- `get_article_filter()` ファクトリ関数で `Depends()` に接続
- `PaginationQueryParser` と組み合わせてページネーション
- 11 テスト通過

## テスト結果

全 11 テスト通過（修正後）。

## Friction Points

### FP1: `PaginationQueryParser.as_depends()` が存在しない（ドキュメントとの乖離）

**状況**: 他のパーサー系クラスで `as_depends()` ファクトリパターンを使うケースがあり（FT83 など）、`PaginationQueryParser.as_depends()` を試みたが `AttributeError`。

正しい使い方は:
```python
# ✅ Annotated スタイル
pagination: Annotated[PaginationQueryParser, Depends()]

# ❌ as_depends() は存在しない
pagination: PaginationQueryParser = Depends(PaginationQueryParser.as_depends())
```

**影響**: `Depends()` の使い方が複数あるため混乱しやすい。how-to ガイドに明記が必要。

### FP2: `Depends()` スタイルとデフォルト値の混在でシンタックスエラー

**状況**: 複数の `Depends()` パラメーターを持つハンドラーで、`= Depends(...)` スタイルと `Annotated[T, Depends()]` スタイルを混在させると `SyntaxError: parameter without a default follows parameter with a default` が出る。

```python
# ❌ SyntaxError
def list_articles(
    filter_: ArticleFilter = Depends(get_article_filter),  # デフォルト値あり
    pagination: Annotated[PaginationQueryParser, Depends()],  # デフォルト値なし
) -> JSONResponse: ...

# ✅ Annotated スタイルに統一
def list_articles(
    filter_: Annotated[ArticleFilter, Depends(get_article_filter)],
    pagination: Annotated[PaginationQueryParser, Depends()],
) -> JSONResponse: ...
```

**影響**: エラーメッセージが直感的でなく、原因がわかりにくい。

## まとめ

摩擦の原因はドキュメント不足。FP1・FP2 を how-to ガイドに追記する Issue を起票する。コード修正は不要。
