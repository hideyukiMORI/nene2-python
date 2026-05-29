# FT255: sqlite3 — パラメータ化クエリ vs SQL インジェクション

**日付**: 2026-05-29
**テーマ**: Python `sqlite3` のパラメータ化クエリと SQL インジェクション対策の実装と検証
**セキュリティ診断**: 🔒 あり（255 % 3 = 0）
**クラッカーペンテスト**: なし（255 % 4 = 3）

---

## 概要

SQL インジェクションは最重要の Web 脆弱性の一つ。`sqlite3` を題材に、**パラメータ化クエリ（`?` プレースホルダ）**で注入文字列を「データ」として扱い、コードとして解釈させない設計を検証した。CLAUDE.md ポリシー（「SQL はパラメータ化クエリのみ。文字列フォーマット禁止」）の実証。

| 危険 | 安全（本 FT） |
|---|---|
| `f"... WHERE name='{name}'"` | `execute("... WHERE name = ?", (name,))` |
| 文字列連結で SQL を組む | プレースホルダで値束縛 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft255-sqlite3/`

| 関数 | 概要 |
|---|---|
| `_seed_connection()` | リクエストごとに in-memory DB を seed（ステートレス） |
| `search_users()` | `?` プレースホルダで検索、テーブル無傷を確認 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/db/search` | パラメータ化クエリでユーザー検索 |

---

## 摩擦点

### F-1: `?` プレースホルダで値を束縛する（文字列フォーマット禁止）

**観察**: `execute(f"SELECT * FROM users WHERE name='{name}'")` は `name = "' OR '1'='1"` で全件取得、`"'; DROP TABLE users;--"` でテーブル破壊につながる。文字列連結/f-string で SQL を組むのが SQL インジェクションの根本原因。

**対処**: `execute("SELECT name FROM users WHERE name = ?", (name,))` で値を束縛。`name` は SQL 構文として解釈されず**リテラルデータ**として扱われる。診断で 9 種の注入がすべて無効化（matches=[]・table_intact=True）。

### F-2: `execute` は単文のみ — 複文インジェクションが効かない

**観察**: `sqlite3` の `execute()` は**1 つの SQL 文のみ**実行する（複数文は `executescript` が必要）。`"'); DELETE FROM users;--"` のような複文注入も、そもそも複文として実行されない（加えてプレースホルダで値束縛）。

**対処**: 通常クエリは `execute`（単文）を使い、`executescript` をユーザー入力で使わない。診断で DROP/DELETE 後も table_intact=True を確認。

### F-3: `LIKE` ワイルドカードと `=` の違い

**観察**: `=` 比較では `%`・`_` はリテラル文字。`LIKE` を使う場合は `%`/`_` がワイルドカードになり、ユーザー入力の `%` で全件マッチや ReDoS 的挙動が起きる（LIKE インジェクション）。

**対処**: 完全一致は `=`（本 FT）。`LIKE` 検索が必要なら `%`/`_` をエスケープ（`ESCAPE` 句）する。診断で `%` が `=` では無効（matches=[]）を確認。

---

## セキュリティ診断結果

| 注入ペイロード | 結果 |
|---|---|
| `alice`（正常） | matches=['alice'] / intact=True |
| `' OR '1'='1` | matches=[] / intact=True |
| `' OR 1=1 --` | matches=[] / intact=True |
| `'; DROP TABLE users;--` | matches=[] / **intact=True**（破壊なし） |
| `' UNION SELECT role FROM users--` | matches=[] / intact=True |
| `alice'--` | matches=[] / intact=True |
| `%`（ワイルドカード） | matches=[] / intact=True |
| `alice' OR name='bob` | matches=[] / intact=True |
| `'); DELETE FROM users;--` | matches=[] / **intact=True**（削除なし） |
| 検索語 201 文字 | **422** |
| セキュリティヘッダー | 付与あり |

**総合評価: 合格**

パラメータ化クエリで全注入を「リテラルデータ」化し、`execute` の単文制約と合わせて SQL インジェクション（OR バイパス・DROP/DELETE・UNION）を完全遮断。CLAUDE.md の SQL ポリシーを実証。

---

## テスト結果

```
5 passed in 0.84s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

SQL インジェクションの怖さと、`?` で防げることを体感できる。f-string で SQL を組む誘惑に注意。

**ドキュメント理解**: なぜ f-string がダメかをコメントで明示。
**事故リスク（高）**: f-string/文字列連結で SQL を組む。
**規約の使いやすさ**: name → matches が明快。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

生 SQL を書く場面で f-string を使いがち。パラメータ化が習慣化していないと事故る。

**コピペ可能性**: `?` プレースホルダパターンは必須知識。
**拡張時の罠**: 動的な IN 句・ORDER BY 列名（プレースホルダ不可な箇所は許可リスト）。
**事故リスク（高）**: 文字列連結。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

ORM/prepared statement に慣れているが、生 SQL のリスクを理解する契機。

**エラーレスポンスの質**: 超過は 422、注入は空結果。
**Python 固有概念**: DB-API の `?` / `:name` プレースホルダ。
**事故リスク（低）**: パラメータ化で防御。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

通常は ORM（SQLAlchemy）。生 SQL を書くなら必ずパラメータ化。列名/テーブル名はプレースホルダ不可なので許可リスト。nene2 は SqlAlchemyQueryExecutor を持つ。

**他フレームワークとの差異**: ORM がデフォルトでパラメータ化。生 SQL はアプリ責任。
**nene2 の薄さへの評価**: パラメータ化の徹底と単文制約の活用が適切。
**事故リスク（低）**: 全注入を遮断。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- SQL を f-string/`%`/`.format`/連結で組んでいないか（パラメータ化必須）。
- 列名・テーブル名・ORDER BY 等プレースホルダ不可な箇所を許可リストで縛っているか。
- `executescript` をユーザー入力で使っていないか。
- LIKE 検索のワイルドカードエスケープ。

**チームでの安全なパターン**: ORM 優先、生 SQL はパラメータ化、識別子は許可リスト。lint/レビューで文字列連結 SQL を禁止。
**事故リスク（低）**: 全注入を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: 「SQL はパラメータ化クエリのみ。文字列フォーマット禁止」を完全実証。Pydantic 制限・`ValidationException` 変換・`logging` 使用も準拠。
**初心者でも安全な API 達成度**: パラメータ化を関数内に固定し、文字列連結 SQL の余地を排除。
**改善提案**: 「パラメータ化できない箇所（識別子・LIMIT・ORDER BY）は許可リスト」を how-to に明記し、`nene2.database` の使用を推奨する。
