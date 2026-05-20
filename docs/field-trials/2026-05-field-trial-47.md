# Field Trial 47: SqlAlchemyTransactionManager.transactional() 実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.8 時点
**テーマ**: `transactional()` コールバックパターンで複数テーブルへの同一トランザクション書き込みと、失敗時のロールバックを FastAPI エンドポイント経由で確認

---

## 概要

銀行振込（送金元残高減算 + 送金先残高増加 + 転送ログ挿入の 3 操作）を
`SqlAlchemyTransactionManager.transactional()` の単一トランザクションで実装した。
残高不足・存在しない口座での失敗時にすべての操作がロールバックされることを確認した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft47-transaction-manager/` に以下を作成:

- **`app.py`** — 口座管理 + 振込 API、`SqlAlchemyTransactionManager.transactional()` で複数書き込み
- **`test_app.py`** — 正常振込・残高更新・不足残高・存在しない口座・重複名 (7 件)
- **`test_friction.py`** — 摩擦点の確認テスト (4 件)

**テスト結果**: 11 件全通過 ✅

---

## 摩擦点

### FP47-1: コールバックは DatabaseQueryExecutorInterface を受け取る

**分類**: 摩擦なし（良い設計の確認）

`transactional(callback)` のコールバックは `DatabaseQueryExecutorInterface` を引数として受け取る。
内部的には `_BoundQueryExecutor` として同一接続にバインドされており、
`fetch_one()` / `write()` を呼ぶことで同一トランザクション内で複数操作できる。

**判断**: SQLAlchemy Core を抽象化したインターフェースが自然に機能する。

---

### FP47-2: ドメイン例外も transactional() を自動ロールバックさせる

**分類**: 摩擦なし（良い設計の確認）

コールバック内で `InsufficientFundsError` のような非 DB 例外を raise した場合、
`engine.begin()` コンテキストマネージャーが自動でロールバックしてから例外を伝播する。
`ErrorHandlerMiddleware` がこれを `SimpleDomainHandler` でキャッチして適切な HTTP レスポンスを返す。

**判断**: 設計通り。「例外発生 = ロールバック」が保証されているため、コールバック内で
ガード条件をチェックして素直に raise するだけで整合性が保たれる。

---

### FP47-3: 複数 write はすべて成功かすべてロールバックか（ACID 保証）

**分類**: 摩擦なし（良い設計の確認）

送金処理の 3 つの write（送金元減算 / 送金先加算 / ログ挿入）は
`transactional()` が提供する `_BoundQueryExecutor` を通じて同一トランザクションで実行される。
途中で例外が発生した場合、実行済みの write も含めてすべてロールバックされる。

**判断**: ACID の Atomicity が正しく動作することを確認した。

---

### FP47-4: transactional() の戻り値はコールバックの戻り値

**分類**: 摩擦なし（設計の確認）

`transactional()` はジェネリクス `[T]` を使ってコールバックの戻り値型を保持する。
コミット後の戻り値（`dict[str, object]` など）をそのまま受け取り、
FastAPI ハンドラーで `JSONResponse` に変換できる。

**判断**: 型安全なコールバックパターンが正しく動作する。

---

## フレームワーク変更

なし（全て設計通りの挙動）

---

## 関連

- `nene2.database.SqlAlchemyTransactionManager` (FT16, v1.7.0)
- `nene2.database.DatabaseQueryExecutorInterface`
- `nene2.database.DatabaseIntegrityException` (FT16, v1.7.0)
- FT16 (TransactionManager 実装, v1.7.0)
- FT38 (トランザクション管理確認, v1.8.5)
- FT46 (DatabaseIntegrityException 実運用, v1.8.8)
