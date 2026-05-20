# Field Trial 34: DatabaseIntegrityException + SimpleDomainHandler 実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.3 時点
**テーマ**: UNIQUE 制約違反 → `DatabaseIntegrityException` → `SimpleDomainHandler` → 409 Problem Details のパイプライン実運用検証

---

## 概要

SQLite UNIQUE 制約を持つ `users` テーブルに `SqlAlchemyQueryExecutor` でアクセスし、
重複 username の登録が自動的に `DatabaseIntegrityException` へ変換され、
`SimpleDomainHandler` が 409 Conflict Problem Details を返す完全なパイプラインを検証した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft34-db-integrity/` に以下を作成:

- **`app.py`** — SQLite インメモリ DB + `SqlAlchemyQueryExecutor` + `SimpleDomainHandler` による UNIQUE 違反ハンドリング
- **`test_app.py`** — 正常系・409・Problem Details 構造・バリデーションエラー混在 (6 件)
- **`test_friction.py`** — 摩擦点の確認テスト (4 件)

```python
handlers = [
    SimpleDomainHandler(
        DatabaseIntegrityException,
        "username-already-taken",
        "Username Already Taken",
        409,
        detail="このユーザー名はすでに使用されています",
    ),
]
app.add_middleware(ErrorHandlerMiddleware, domain_handlers=handlers)
```

**テスト結果**: 10 件全通過 ✅

---

## 摩擦点

### FP34-1: `DatabaseIntegrityException` のメッセージが SQLAlchemy の生テキスト

**分類**: 既知の制約（摩擦あり・軽微）

```
(sqlite3.IntegrityError) UNIQUE constraint failed: users.username
```

どのフィールドが重複したかを取り出すには文字列パースが必要。
DB エンジンごとにメッセージ形式が異なる（SQLite / MySQL / PostgreSQL）。

**判断**: フレームワーク側でフィールド抽出 API を提供することも可能だが、
エンジン依存のパースロジックを組み込むと移植性が下がる。
アプリ側でドメイン固有の例外（`UsernameTakenException` など）に変換するパターンを推奨。

---

### FP34-2: 制約種別を示すサブクラスがない

**分類**: 既知の制約（摩擦あり・軽微）

`DatabaseIntegrityException` は UNIQUE / FK / CHECK 制約を区別しない。
違反種別で異なるレスポンスを返したい場合は文字列パースが必要。

**判断**: 制約種別サブクラスの追加は有用だが、DB エンジンごとの判定ロジックが複雑になる。
現時点はアプリ側で try/except してドメイン例外に変換する方針を how-to ドキュメントで説明。

---

### FP34-3: テスト用インメモリ SQLite に `StaticPool` が必要

**分類**: 摩擦あり → **ドキュメント対応**

`SqlAlchemyQueryExecutor` はクエリごとに `engine.begin()` / `engine.connect()` で
コネクションを開く。`sqlite:///:memory:` はコネクションごとに独立した DB を作成するため、
`StaticPool` なしではクエリ間でテーブルが見えなくなる場合がある。

```python
# 推奨パターン
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

**対応**: `docs/how-to/run-tests.md` に `StaticPool` 使用を明記。

---

### FP34-4: `SimpleDomainHandler` は制約種別を区別できない

**分類**: 設計通り（摩擦なし）

`SimpleDomainHandler` は例外クラスのみで判定する。
UNIQUE 違反と FK 違反を別々の HTTP ステータスにマップしたい場合は
`DomainExceptionHandlerProtocol` を実装する必要がある。

**判断**: `SimpleDomainHandler` はシンプルケース専用のヘルパーという設計意図通り。
複雑なケースには Protocol 実装を使うのが正しい。

---

## フレームワーク変更

- `docs/how-to/run-tests.md` に `StaticPool` パターンを追記 (FP34-3 対応)

---

## 関連

- `nene2.database.DatabaseIntegrityException`
- `nene2.database.SqlAlchemyQueryExecutor`
- `nene2.middleware.SimpleDomainHandler`
- FT16 (DatabaseIntegrityException 実装, v1.7.0)
- FT21 (SimpleDomainHandler 実装, v1.8.0)
