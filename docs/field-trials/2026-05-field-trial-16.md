# Field Trial 16 — transactional(callback) パターン実運用

**Date:** 2026-05-20
**App:** 銀行口座送金 API（送金元の残高を減らして送金先に加算する atomic 操作）
**Directory:** `/home/xi/docker/nene2-python-FT/ft16-transaction/`
**nene2-python version:** v1.6.0

## 概要

`transactional(callback)` パターンを実際の送金ユースケースに適用し、
ロールバック挙動・例外処理・async コンテキストとの相互作用を検証した。

## 動作確認結果

- `transactional(callback)` が atomic に実行されること ✓
- `CHECK 制約違反`（残高 < 0）発生時に全操作がロールバックされること ✓
- `UNIQUE 制約違反`（IntegrityError）でもロールバックが正しく行われること ✓
- SQLite `:memory:` + `StaticPool` で `SqlAlchemyQueryExecutor` と `SqlAlchemyTransactionManager` を同一 DB に向けられること ✓

## 摩擦点

### FT16-F1 (MEDIUM, API一貫性): IntegrityError が DatabaseConnectionException にラップされない

`SqlAlchemyTransactionManager.transactional()` は `OperationalError` のみを
`DatabaseConnectionException` に変換し、`IntegrityError`（UNIQUE 制約違反・FK 制約違反など）は
生の SQLAlchemy 例外として呼び出し側に伝播する。

UseCase 層でフレームワーク独自例外に統一されていないため、
呼び出し元が SQLAlchemy の例外型に依存した `except IntegrityError` を書く必要がある。

```python
from sqlalchemy.exc import IntegrityError

with pytest.raises(IntegrityError):  # 摩擦: SQLAlchemy 依存が漏れ出す
    tx_manager.transactional(_duplicate_insert)
```

**対応案**: `IntegrityError` も `DatabaseConnectionException`（または新設の `DatabaseIntegrityException`）にラップする。または `transactional()` がキャッチすべき SQLAlchemy 例外一覧をドキュメントに明記する。

### FT16-F2 (LOW, 非同期対応): async コンテキストから transactional() を呼ぶとイベントループをブロックする

`SqlAlchemyTransactionManager.transactional()` は同期 API であるため、
FastAPI の `async def` ハンドラーから直接呼ぶとイベントループをブロックする。
現状の実装でも動作はするが、高負荷時にパフォーマンス劣化の原因になりうる。

```python
@app.post("/transfer")
async def transfer(...) -> JSONResponse:
    # 同期 transactional() を直接呼んでいる（イベントループブロッキング）
    result = transfer_uc.execute(...)
```

**対応案**: `asyncio.to_thread()` でのラップをドキュメントに記載する。
または `AsyncSqlAlchemyTransactionManager` を将来的に追加する（SQLAlchemy async core を利用）。

## まとめ

コアの atomic 保証（コミット・ロールバック）は期待通りに機能した。
摩擦は例外ハンドリングの API 一貫性（F1: MEDIUM）と非同期対応（F2: LOW）の2点。

F1 は UseCase 層が SQLAlchemy に依存するアーキテクチャ上の問題であり、
Clean Architecture の原則に照らして対応が必要。
