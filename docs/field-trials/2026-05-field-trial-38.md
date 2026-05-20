# Field Trial 38: SqlAlchemyTransactionManager.transactional() 実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.4 時点
**テーマ**: 注文作成（在庫更新 + 注文レコード作成）をトランザクションで包み、途中での例外発生時のロールバック動作を確認する

---

## 概要

`SqlAlchemyTransactionManager.transactional(callback)` を使って複数の DB 書き込みを一つのトランザクションに包み、途中で例外が発生した場合のロールバック動作を検証した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft38-transactions/` に以下を作成:

- **`app.py`** — 在庫チェック + 在庫減少 + 注文作成を `transactional()` で包んだ注文 API
- **`test_app.py`** — 正常注文・在庫不足・ロールバック確認・連続注文 (6 件)
- **`test_friction.py`** — 摩擦点の確認テスト (3 件)

**テスト結果**: 9 件全通過 ✅

---

## 摩擦点

### FP38-1: コールバック内で型アノテーションに `DatabaseQueryExecutorInterface` が必要

**分類**: 軽微な摩擦（mypy --strict 使用時）

```python
def _do_create(db: object) -> int:
    ...
```

`db` を `object` 型にするとメソッド呼び出しに mypy エラーが出る。
`DatabaseQueryExecutorInterface` をインポートして型アノテーションする必要がある。

**判断**: mypy --strict の設計上当然の制約。インポートはやや冗長だが許容範囲。
`db: DatabaseQueryExecutorInterface` が推奨パターンとしてドキュメントに記載されている。

---

### FP38-2: savepoint（ネストトランザクション）はサポートしない

**分類**: 既知の制約（設計通り）

`DatabaseQueryExecutorInterface` が持つのは `fetch_all` / `fetch_one` / `write` のみ。
SQLAlchemy の savepoint 機能（`SAVEPOINT` / `ROLLBACK TO SAVEPOINT`）は使えない。

**判断**: フレームワークの抽象化レイヤーが Pure SQL テキストベースの設計を採用しているため、
ORM/Connection 固有の高度な機能は意図的に除外されている。
savepoint が必要な場合は SQLAlchemy を直接使う Repository を実装するのが正しいパターン。

---

### FP38-3: トランザクション途中の例外はすべてロールバックされる（設計通り）

**分類**: 設計通り（摩擦なし）

```python
def _callback(db: DatabaseQueryExecutorInterface) -> None:
    db.write("INSERT ...")  # ← この変更も
    raise ValueError("oops")  # ← ここで例外 → 全部ロールバック
```

例外の種類に関わらず（`DatabaseIntegrityException` 以外でも）全変更がロールバックされる。
これは `SqlAlchemyTransactionManager.transactional()` の期待される動作。

---

## フレームワーク変更

なし（全て設計通りの挙動）

---

## 関連

- `nene2.database.SqlAlchemyTransactionManager`
- `nene2.database.DatabaseQueryExecutorInterface`
- FT16 (DatabaseIntegrityException, v1.7.0)
- FT34 (DatabaseIntegrityException 実運用, v1.8.3)
