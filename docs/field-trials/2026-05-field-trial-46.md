# Field Trial 46: DatabaseIntegrityException 実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.8 時点
**テーマ**: `DatabaseIntegrityException` を FastAPI エンドポイント経由で UNIQUE 制約・FK 制約違反を処理するパターンの実運用確認

---

## 概要

`SqlAlchemyQueryExecutor` を使って SQLite への UNIQUE/FK 制約違反を発生させ、
`DatabaseIntegrityException` を `DuplicateEmailError` / `InvalidUserReferenceError` に
サブクラス化してドメイン例外に変換し、`SimpleDomainHandler` で HTTP レスポンスにマッピングするパターンを実装した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft46-db-integrity/` に以下を作成:

- **`app.py`** — SQLite + `SqlAlchemyQueryExecutor` (Core API) を使ったユーザー/ポスト管理 API
- **`test_app.py`** — 正常系・UNIQUE 違反 409・FK 違反 422・エラー後回復 (7 件)
- **`test_friction.py`** — 摩擦点の確認テスト (4 件)

**テスト結果**: 11 件全通過 ✅

---

## 摩擦点

### FP46-1: DatabaseIntegrityException のサブクラス化が必要

**分類**: 軽微な摩擦（パターン提示）

`DatabaseIntegrityException` は汎用例外のため、UNIQUE 制約違反（409）と FK 制約違反（422）を
別の HTTP ステータスコードにマッピングするには、サブクラスを作って例外を変換する必要がある。

```python
class DuplicateEmailError(DatabaseIntegrityException): pass
class InvalidUserReferenceError(DatabaseIntegrityException): pass

try:
    executor.write("INSERT INTO users ...", params)
except DatabaseIntegrityException as exc:
    raise DuplicateEmailError(str(exc)) from exc
```

**判断**: データベース例外に対してドメイン固有の意味付けをするパターンとして自然。
`IntegrityError` のメッセージを解析して違反種別を判定する方法もあるが、
SQLite/MySQL/PostgreSQL でメッセージ形式が異なるため移植性に課題がある。
サブクラス + 明示的 raise パターンが最も移植性が高い。

---

### FP46-2: SQLite の FK 制約は PRAGMA foreign_keys=ON が必要

**分類**: 注意喚起（既知事項・ドキュメント追記価値あり）

SQLite のデフォルトでは外部キー制約が無効。
`create_engine()` 後に `PRAGMA foreign_keys=ON` を実行しないと、
FK 制約違反がスルーされて孤児レコードが挿入される。

```python
with engine.begin() as conn:
    conn.execute(text("PRAGMA foreign_keys=ON"))
```

`StaticPool` を使う場合は最初の接続でこれを実行すれば全接続に適用される。

**判断**: SQLite 特有の注意点。`docs/how-to/run-tests.md` の StaticPool セクションに追記する価値がある。

---

### FP46-3: 整合性エラー後もトランザクションは自動ロールバックされる

**分類**: 摩擦なし（良い設計の確認）

`DatabaseIntegrityException` が発生すると `SqlAlchemyQueryExecutor.write()` 内で
`engine.begin()` のコンテキストマネージャーがロールバックする。
次のリクエストでは新しいトランザクションが開始されるため、セッション汚染は発生しない。

**判断**: SQLAlchemy Core の設計通り。`engine.begin()` を使ったパターンは安全。

---

### FP46-4: SqlAlchemyQueryExecutor は SQL 文字列 API であり ORM Session ではない

**分類**: 摩擦あり（設計の理解不足・初回実装で失敗）

当初 `SqlAlchemyQueryExecutor.write()` に ORM の `Session` を使ったコールバックを渡そうとしたが、
`write()` は SQL 文字列 + params を受け取る Core API であることを確認した。

```python
# NG: コールバックパターン（TransactionManager のもの）
executor.write(lambda session: session.add(row))  # TypeError

# OK: SQL 文字列パターン（QueryExecutor のもの）
executor.write("INSERT INTO users (email) VALUES (:email)", {"email": "..."})
```

ORM (Session) を使うパターンは `SqlAlchemyTransactionManager.transactional(callback)` で、
コールバック内では `_BoundQueryExecutor` を通じて SQL を実行する。
直接 Session を使いたい場合はフレームワーク外で SQLAlchemy ORM を使う。

**判断**: フレームワークの設計通り（SQLAlchemy Core ベース）。
ドキュメントに Core API と ORM の違いを明記する価値がある。

---

## フレームワーク変更

なし（全て設計通りの挙動）

ドキュメント追記を検討:
- `docs/how-to/run-tests.md` の StaticPool セクションに SQLite FK pragma を追記
- `docs/how-to/` に `DatabaseIntegrityException` ハンドリングパターン how-to を追加

---

## 関連

- `nene2.database.DatabaseIntegrityException` (FT16, v1.7.0)
- `nene2.database.SqlAlchemyQueryExecutor`
- `nene2.database.SqlAlchemyTransactionManager`
- `nene2.middleware.SimpleDomainHandler` (FT21, v1.8.0)
- FT16 (DatabaseIntegrityException 実装, v1.7.0)
- FT17 (SqlAlchemyQueryExecutor.write() バグ修正, v1.7.0)
- FT34 (StaticPool SQLite テスト, v1.8.4)
