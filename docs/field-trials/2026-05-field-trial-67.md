# FT67: SqlAlchemyTransactionManager 実運用検証

**日付**: 2026-05-20  
**テーマ**: トランザクション管理 (`SqlAlchemyTransactionManager`) の実運用確認  
**バージョン**: v1.8.17 → v1.8.18 (ドキュメント追加)  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft67-transaction-manager/`

---

## 概要

`nene2.database.SqlAlchemyTransactionManager` を使って口座振替アプリを実装し、
`transactional()` コールバック API・ロールバック動作・コミット確認を検証した。

---

## 実装内容

- SQLite in-memory DB に `accounts` テーブルを作成
- `transactional(callback)`: 振替処理を 1 トランザクションで実行
- 残高不足時は `ValueError` を raise → ロールバック
- GET `/accounts/{name}` と POST `/transfers` エンドポイント

---

## テスト結果

**7/7 passed** (StaticPool 修正後)

| テスト | 結果 |
|---|---|
| `test_get_existing_account` | PASSED |
| `test_get_nonexistent_account_returns_404` | PASSED |
| `test_successful_transfer` | PASSED |
| `test_insufficient_balance_returns_422` | PASSED |
| `test_transaction_rollback_on_error` | PASSED |
| `test_transfer_to_nonexistent_account` | PASSED |
| `test_transactional_commits_on_success` | PASSED |

---

## Friction Points

### FP-1: SQLite `:memory:` と `SqlAlchemyQueryExecutor` の接続分離問題

**発生箇所**: `setup_db()` でテーブル作成後、`executor.fetch_one()` が `no such table: accounts` エラー

**症状**:
```
DatabaseConnectionException: (sqlite3.OperationalError) no such table: accounts
```

**原因**: SQLAlchemy のデフォルトコネクションプールでは `sqlite:///:memory:` への接続ごとに
新しいインメモリDBが生成される。`setup_db()` と `executor.fetch_one()` が別DBを参照する。

**修正**:
```python
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

`SqlAlchemyQueryExecutor` の docstring に注意書きを追加 (Issue #305, v1.8.18)。

---

## 結論

`SqlAlchemyTransactionManager.transactional()` は実運用で問題なく使用できる。
コールバック内の例外でロールバックが正しく機能することも確認。
SQLite in-memory DB 使用時の `StaticPool` 要件はドキュメント化済み。
