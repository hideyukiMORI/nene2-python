# FT163: sqlite3 モジュール

**日付**: 2026-05-21
**テーマ**: `sqlite3` モジュール — 基本 CRUD、executemany、Row オブジェクト、lastrowid/rowcount、カスタム関数・アグリゲート、トランザクション

---

## 概要

Python 標準ライブラリの `sqlite3` モジュールを nene2-python フレームワーク上で検証した。
`sqlite3` は SQLite データベースへのインターフェースを提供し、
`:memory:` データベースと組み合わせることで外部ファイルなしに
インメモリで RDBMS 機能を検証できる。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft163-sqlite3/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `basic_crud_demo()` | INSERT/SELECT/UPDATE/DELETE の基本 CRUD |
| `bulk_insert_demo(items)` | `executemany` でバルクインサート |
| `row_factory_demo()` | `sqlite3.Row` で列名アクセス・辞書変換 |
| `insert_metadata_demo()` | `lastrowid` と `rowcount` の検証 |
| `custom_function_demo(texts)` | `create_function` でカスタム SQL 関数を登録 |
| `custom_aggregate_demo(texts)` | `create_aggregate` でカスタムアグリゲートを登録 |
| `transaction_rollback_demo()` | ロールバックの動作検証 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/sqlite/basic-crud` | 基本 CRUD デモ |
| POST | `/sqlite/bulk-insert` | executemany バルクインサート |
| GET | `/sqlite/row-factory` | sqlite3.Row デモ |
| GET | `/sqlite/insert-metadata` | lastrowid / rowcount デモ |
| POST | `/sqlite/custom-function` | カスタム SQL 関数デモ |
| POST | `/sqlite/custom-aggregate` | カスタムアグリゲートデモ |
| GET | `/sqlite/transaction-rollback` | トランザクション・ロールバックデモ |

---

## テスト結果

**26 passed（摩擦ゼロ）**

```
26 passed in 0.70s
```

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

---

## 観察点

### 観察1: `:memory:` データベースでファイルシステム不要

```python
with sqlite3.connect(":memory:") as conn:
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO t VALUES (1, 'hello')")
```

`:memory:` を指定するとファイルを作成せずにインメモリで SQLite DB を使用できる。
テストやプロトタイプに最適。コネクション終了時にデータは消える。

### 観察2: `row_factory = sqlite3.Row` で列名アクセス

```python
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT id, name FROM t").fetchone()
name = row["name"]    # 列名でアクセス
name = row[1]         # インデックスでもアクセス可
d = dict(row)         # 辞書に変換
keys = list(row.keys())  # 列名一覧
```

デフォルトの `tuple` ではなく `Row` オブジェクトを使うことで、
より可読性の高いコードが書ける。JSON シリアライズ時は `dict(row)` に変換する。

### 観察3: `create_function` で Python 関数を SQL 内で使用

```python
conn.create_function("upper_len", 1, lambda s: len(s.upper()))
conn.execute("SELECT upper_len(name) FROM t")
```

第2引数は引数の数（`-1` で可変長）。
Python の任意のロジックを SQL クエリ内で使用できる。
nene2 の実際の利用場面: テキスト正規化、カスタム集計など。

### 観察4: `create_aggregate` でカスタム集計関数

```python
class MyAgg:
    def __init__(self) -> None:
        self.total = 0
    def step(self, value: int) -> None:
        self.total += value
    def finalize(self) -> int:
        return self.total

conn.create_aggregate("my_sum", 1, MyAgg)
conn.execute("SELECT my_sum(value) FROM t")
```

`step()` メソッドが各行で呼ばれ、`finalize()` が集計結果を返す。
Python クラスで SQL の GROUP BY と組み合わせたカスタム集計が実現できる。

### 観察5: `with sqlite3.connect() as conn` はトランザクション管理

```python
with sqlite3.connect(":memory:") as conn:
    conn.execute("INSERT ...")
    # ブロック終了時に自動 COMMIT
    # 例外発生時は自動 ROLLBACK
```

ただし、コンテキストマネージャーはトランザクションのみ管理し、
**コネクションはクローズしない**（`sqlite3` 特有の挙動）。
明示的なロールバックには `conn.rollback()` を呼ぶ。

### 観察6: `lastrowid` と `rowcount` の活用

```python
cur = conn.execute("INSERT INTO t VALUES (?, ?)", ("name", 42))
new_id = cur.lastrowid    # 挿入された行の ROWID

cur2 = conn.execute("UPDATE t SET value = 99")
affected = cur2.rowcount  # 影響を受けた行数
```

`lastrowid` は `INSERT` のみ有効。`rowcount` は `UPDATE`/`DELETE` で有効。

---

## nene2-python フレームワークとの統合

- nene2 は SQLAlchemy をラップした `SqlAlchemyQueryExecutor` を提供するが、
  `sqlite3` モジュールを直接使うことで SQLAlchemy オーバーヘッドなしの軽量 DB 処理が可能
- `ErrorHandlerMiddleware` + `RequestIdMiddleware` は問題なく機能
- すべてインメモリ DB を使用しているため副作用なし

---

## まとめ

`sqlite3` モジュールは `:memory:` データベース、`Row` ファクトリ、
カスタム関数・アグリゲート登録など豊富な機能を提供する。
nene2 の SQLAlchemy 層とは独立に使えるため、
軽量なデータ処理や設定ストレージとして活用できる。摩擦ゼロで実装完了。
