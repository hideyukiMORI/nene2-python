# Field Trial 17 — 複数ドメイン連携実運用

**Date:** 2026-05-20
**App:** タスク管理API（Task + Category の2ドメイン連携）
**Directory:** `/home/xi/docker/nene2-python-FT/ft17-multi-domain/`
**nene2-python version:** v1.6.0 (local dev build)

## 概要

Task（タスク）と Category（カテゴリ）の2ドメインを連携させたアプリを実装し、
`SqlAlchemyQueryExecutor.write()` と `DatabaseIntegrityException`、
`transactional(callback)` の混在パターンの DX を検証した。

## 動作確認結果

- カテゴリ一覧・タスク一覧・カテゴリでのフィルタリングが動作すること ✓
- タスク完了（UPDATE）操作が正常に機能すること ✓（ただし FT17-F2 の制約あり）
- `transactional()` 内の `IntegrityError` が `DatabaseIntegrityException` に変換されること ✓

## 摩擦点

### FT17-F1 (HIGH, バグ): SqlAlchemyQueryExecutor.write() が IntegrityError をキャッチしない

`_BoundQueryExecutor.write()`（`transactional()` 内部で使われる）は FT16 で `IntegrityError` を
`DatabaseIntegrityException` に変換するよう修正されたが、
`SqlAlchemyQueryExecutor.write()`（直接呼び出し）は対応していない。

同じ「INSERT が重複するケース」でも、使う API によって異なる例外型が飛ぶ：

```python
# 直接 write() → IntegrityError (SQLAlchemy)
executor.write("INSERT INTO categories (name) VALUES (:name)", {"name": "dup"})

# transactional() 内 write() → DatabaseIntegrityException (nene2)
tx_manager.transactional(lambda ex: ex.write("INSERT INTO categories (name) VALUES (:name)", {"name": "dup"}))
```

UseCase 層でどちらの API を使うかによって `except` 節を変える必要があり、一貫性がない。

**対応**: `SqlAlchemyQueryExecutor.write()` でも `IntegrityError` をキャッチして
`DatabaseIntegrityException` にラップする。

### FT17-F2 (HIGH, バグ): write() が UPDATE/DELETE で 0 行影響した場合に誤った値を返す

`write()` は `result.lastrowid or result.rowcount` を返すが、SQLite では UPDATE/DELETE の後も
`cursor.lastrowid` が前の INSERT の rowid を保持する。

```python
# DB に id=1 の行がある状態で
result = executor.write("UPDATE items SET name = 'x' WHERE id = 999")  # 0行影響
# result == 1 (前のINSERTのlastrowid) — 期待値は 0
```

`if affected == 0: raise NotFound` のパターンが正しく動かない。

**対応**: SQL が `INSERT` で始まる場合のみ `lastrowid` を使い、UPDATE/DELETE は `rowcount` を返す。

## まとめ

ドメイン間連携（JOIN クエリ、カテゴリフィルタリング）は問題なく動作した。
ただし `SqlAlchemyQueryExecutor.write()` に HIGH レベルのバグが2件あり:

- FT17-F1: `IntegrityError` が `DatabaseIntegrityException` に変換されない（API 非対称）
- FT17-F2: UPDATE/DELETE で 0 行影響した場合の戻り値が不正

両方とも `_BoundQueryExecutor.write()` には修正済みだが、`SqlAlchemyQueryExecutor.write()` に未適用。
