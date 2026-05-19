# Field Trial 2 — bookshelf: SQLite永続化リポジトリの DX 検証

## Date

2026-05-19

## Baseline

- nene2-python v0.1.0 (`uv add git+https://github.com/hideyukiMORI/nene2-python.git`)
- Python 3.14.5（uv managed）
- プロジェクト: **bookshelf** — 書籍管理 JSON API
- エンティティ: `Book`（title, author, isbn, published_year）— 5 エンドポイント（CRUD）
- **`SqlAlchemyBookRepository`（SQLite）** を使用 ← FT1 との差分

## Goal

FT1 は InMemory のみで検証した。FT2 では `SqlAlchemyQueryExecutor` を使う永続化パスを
外部プロジェクトから初めて実装し、DX 上の摩擦点を洗い出す。

---

## Steps Taken

### 1. プロジェクト初期化・インストール

```bash
mkdir nene2-ft2-bookshelf && cd nene2-ft2-bookshelf
uv init --name bookshelf --no-workspace
uv add "nene2-python @ git+https://github.com/hideyukiMORI/nene2-python.git"
```

→ FT1 と同様、問題なし。

### 2. エンティティ・リポジトリ・UseCase・ハンドラ実装

FT1 で修正されたドキュメント（new-project.md, framework-modules.md）を参照しながら実装。
ミドルウェアスタック・`request_validation_error_handler` 登録は FT1 の摩擦修正が効いており
ドキュメント通りに一発で動いた（F-4〜F-7 が解消されていることを確認）。

### 3. SQLite リポジトリ実装

`SqlAlchemyQueryExecutor` を使い `SqlAlchemyBookRepository` を実装。
ここで以下の摩擦を発見。

### 4. 動作確認

```bash
PYTHONPATH=src DB_ADAPTER=sqlite DB_NAME=":memory:" uv run uvicorn app:app --port 8082
```

全エンドポイント（LIST / GET / CREATE / UPDATE / DELETE / 404 / 422）が正常動作することを確認。

---

## Friction Points

### F-1 `fetch_one` / `fetch_all` の返り値型から entity へのキャストで `type: ignore` が必要

**severity**: 中  
**type**: 型安全 / DX

`fetch_one()` の返り値は `dict[str, Any]`。値をエンティティに変換する際に
`int(row["id"])` や `str(row["title"])` が必要で、厳密な静的解析環境では
`# type: ignore[arg-type]` を付けることになる。

```python
# 毎回このパターンを手書きする
return Book(
    id=int(row["id"]),          # type: ignore[arg-type]
    title=str(row["title"]),
    ...
)
```

ガイドもなく、開発者が自己流で書くことになる。

**Follow-up**: ドキュメントに `_row_to_book()` ヘルパーパターンを推奨例として追記する。

---

### F-2 スキーマ定義（`CREATE TABLE`）を自前で書く必要があり、指針がない

**severity**: 高  
**type**: ドキュメント不足

nene2 は ORM を持たないため、テーブル定義は生 SQL で書くことになる。
`ensure_schema(executor)` という関数を自前で実装したが、この慣習はドキュメントに記載がなく、
「どこに書くべきか」「どう呼ぶべきか」が不明。

- `schema.py` に書くべきか？`sqlalchemy_repository.py` に書くべきか？
- アプリ起動時に `create_app()` から呼ぶのが正しいか？
- Alembic を使う場合のパターンは？

**Follow-up**: `SqlAlchemyXxxRepository` のハウツーガイドにスキーマ管理セクションを追加する。

---

### F-3 `SqlAlchemyQueryExecutor.write()` の返り値が `lastrowid` か `rowcount` か文脈依存

**severity**: 中  
**type**: API 設計 / ドキュメント

docstring には「Returns lastrowid for INSERT, affected rowcount for UPDATE/DELETE」と書いてあるが、
外部プロジェクトから見ると：

1. `int` として扱って良いか（`None` になる可能性は？）不明
2. `lastrowid` が `0` になるケース（複数行 INSERT 等）が不明
3. UPDATE/DELETE が 0 件のときの返り値の扱いが不明

実際には `new_id = self._executor.write(...)` で ID として使ったが、型的に `int` と断言できない。

**Follow-up**: `SqlAlchemyQueryExecutor` の docstring を補強 + リファレンスドキュメントに記載。

---

### F-5 `AppSettings.db_url` が何を生成するか外部から見えない

**severity**: 低  
**type**: ドキュメント

`DB_ADAPTER=sqlite`, `DB_NAME=":memory:"` 時に `cfg.db_url` が
`"sqlite+pysqlite:///:memory:"` を返すことはソースを読まないとわからない。

configuration.md に `DB_ADAPTER` 別の `db_url` 生成例を追記すれば解決する。

**Follow-up**: 設定リファレンスに `db_url` の生成例を追記する。

---

## Summary

| ID  | 摩擦                                      | 深刻度 | 種別               | Follow-up Issue |
|-----|-------------------------------------------|--------|--------------------|-----------------|
| F-1 | `dict[str, Any]` → entity キャストパターン不明 | 中     | ドキュメント       | TBD             |
| F-2 | スキーマ管理（`ensure_schema`）の指針なし  | 高     | ドキュメント不足   | TBD             |
| F-3 | `write()` 返り値の型・意味が不明確        | 中     | API/ドキュメント   | TBD             |
| F-5 | `db_url` 生成規則が不透明                 | 低     | ドキュメント       | TBD             |

FT1 で修正した F-4〜F-7（ミドルウェアスタック・`request_validation_error_handler`）は
今回ドキュメント通りに実装でき、**修正が機能していることを確認**。

次回 FT3 は Auth（BearerToken）付きシナリオ、または複数ドメインシナリオを推奨。
