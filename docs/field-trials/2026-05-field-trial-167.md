# FT167: enum モジュール

**日付**: 2026-05-21
**テーマ**: `enum` モジュール — `Enum`・`StrEnum`・`IntEnum`・`Flag`・`auto()`・状態遷移・権限管理
**セキュリティ診断**: なし（167 % 3 = 2）

---

## 概要

Python 標準ライブラリの `enum` モジュールを nene2-python フレームワーク上で検証した。
`enum` はドメインモデルの状態・権限・分類を型安全に表現するための中核モジュール。
`StrEnum`（Python 3.11+）は Pydantic v2 と組み合わせて HTTP 境界での型検証に直接使える。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft167-enum/`

### 主要機能

| クラス/関数 | 概要 |
|---|---|
| `Color(Enum)` | 基本 Enum。値で参照・イテレーション |
| `TaskStatus(StrEnum)` | `auto()` で名前を小文字化。文字列として使用可能 |
| `Priority(IntEnum)` | 比較・算術演算が可能な整数 Enum |
| `Permission(Flag)` | ビットフラグで権限を組み合わせ（READ / WRITE / DELETE / ADMIN） |
| `HttpMethod(StrEnum)` | カスタムプロパティ（`is_safe`, `has_body`）付き |
| `Task` dataclass | `TaskStatus` / `Priority` / `Permission` を持つドメインオブジェクト |
| `transition_task()` | 許可された状態遷移のみ受け付ける型安全な状態機械 |
| `describe_permission()` | `Flag` の組み合わせを人間可読な辞書に変換 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/enum/colors` | 全 Color 一覧 |
| GET | `/enum/task-status` | TaskStatus 一覧・StrEnum 確認 |
| POST | `/enum/transition` | 状態遷移バリデーション |
| GET | `/enum/priority` | Priority 比較 |
| POST | `/enum/permission` | Permission フラグ組み合わせ |
| GET | `/enum/http-method` | HttpMethod プロパティ |

---

## テスト結果

**32 passed（摩擦ゼロ）**

```
32 passed in 1.00s
```

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

---

## 観察点

### 観察1: `StrEnum` + `auto()` で名前を自動的に小文字化

```python
class TaskStatus(enum.StrEnum):
    PENDING = enum.auto()   # → "pending"
    RUNNING = enum.auto()   # → "running"
```

`StrEnum` の `auto()` は `_generate_next_value_()` をオーバーライドして
メンバー名を小文字にする。つまり `TaskStatus.PENDING == "pending"` が成立し、
JSON シリアライズ時に `.value` を呼ぶ必要がない。
Pydantic v2 + FastAPI ではフィールドに `TaskStatus` を指定するだけで HTTP Body・レスポンスで使える。

### 観察2: `Flag` でビット権限管理 — `in` 演算子でチェック

```python
class Permission(enum.Flag):
    READ = enum.auto()       # 1
    WRITE = enum.auto()      # 2
    DELETE = enum.auto()     # 4
    ADMIN = READ | WRITE | DELETE  # 7

rw = Permission.READ | Permission.WRITE
assert Permission.READ in rw      # True
assert Permission.DELETE not in rw  # True
```

`Flag` のビット演算（`|`, `&`, `~`）は直感的で、RBAC の権限チェックに最適。
`Permission.NONE = 0` を定義することで「権限なし」を明示的に表現できる。

### 観察3: `IntEnum` は `int` として比較・ソートできる

```python
assert Priority.LOW < Priority.HIGH   # True（数値比較）
assert Priority.LOW + Priority.MEDIUM == 6  # 算術演算も可
sorted_priorities = sorted([Priority.HIGH, Priority.LOW])  # [LOW, HIGH]
```

DB のカラム値が整数の場合、`IntEnum` を使うと ORM との相互変換がシームレス。
ただし算術演算の結果が `int`（Enum でない）になることに注意。

### 観察4: Enum に `@property` を追加してドメインロジックをカプセル化

```python
class HttpMethod(enum.StrEnum):
    @property
    def is_safe(self) -> bool:
        return self in (HttpMethod.GET,)

    @property
    def has_body(self) -> bool:
        return self in (HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH)
```

Enum にメソッドを追加することで、`if method == "GET":` の散在を防ぎ
ドメインロジックを 1 箇所に集約できる。`@property` との相性も良い。

### 観察5: Pydantic v2 は `StrEnum` を文字列バリデーションとして扱う

```python
class TransitionBody(BaseModel):
    current_status: TaskStatus   # "pending" / "running" / "done" / "failed" のみ許可
    new_status: TaskStatus
```

Pydantic v2 は `StrEnum` フィールドに対して、有効な enum 値のみを受け付け、
無効な値には自動的に 422 を返す。`Literal["pending", "running", ...]` より型安全。

---

## nene2-python フレームワークとの統合

- `TaskStatus(StrEnum)` は nene2 の Note ドメインの `status` フィールドに直接適用できる
- `Permission(Flag)` は `ApiKeyAuthMiddleware` の権限スコープ実装に応用可能
- `Priority(IntEnum)` はタスクスケジューリング・DB ソートに使いやすい
- Enum をレスポンスモデルに含める場合、FastAPI は自動的に `.value` でシリアライズする
- `transition_task()` のようなドメイン状態機械は UseCase 内に実装するパターンが nene2 アーキテクチャと整合する

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`Enum` の基本（`class Color(Enum): RED = "red"`）は直感的に理解できる。
`StrEnum`・`IntEnum`・`Flag` の使い分けは最初は混乱する。

**ドキュメント理解**: 「どれを使えばいいか」の判断基準がなければ基本 `Enum` だけを使い続ける。
nene2 の how-to に「HTTP API の状態フィールドは `StrEnum` を使う」という指針があれば一発で決まる。

**事故リスク**: 低。Enum の誤用は大きな事故にはつながりにくい。
ただし `IntEnum` の算術演算結果が `int` になることを知らず、Enum メンバーを期待してバグになる可能性。

**規約の使いやすさ**: `StrEnum` + `auto()` のパターンはコピペで使える。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

文字列定数の代わりに `"pending"` / `"running"` をそのまま使う習慣がある。
`StrEnum` を知ると「これだけで typo を防げるんだ」と即採用する傾向。

**コピペ可能性**: `StrEnum` + `auto()` のパターンは一度見れば再現できる。

**拡張時の罠**: `Flag` の複合演算（`rw = READ | WRITE`）を見て、
「`|` は OR だから `rw == READ or rw == WRITE` と同じ」と誤解し、
`if rw == READ:` と書いてしまう（`in` を使わなければならない）。

**セキュリティ的な事故リスク**: 中。`Permission.ADMIN = READ | WRITE | DELETE` を定義したつもりが、
ビット演算の順序ミスで意図しない権限の組み合わせになるリスク。テストで確認が必要。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `enum` / `const enum` / `union type` との比較で混乱する可能性。
Python の `Enum` はクラスであり、TS の `enum` より強力（メソッド追加可能）。

**エラーレスポンスの質**: Pydantic が `StrEnum` を自動バリデーションして 422 を返すため、
クライアントには明確なエラーが返る。

**事故リスク**: 低。TS の概念と対応関係が作れる。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `CharField(choices=...)` + `TextChoices` との比較で評価する。
`StrEnum` は `TextChoices` より汎用的で型安全性が高い。

**他フレームワークとの差異**:
- Django: `models.TextChoices` → DB のチョイスとモデルを一元管理
- nene2-python: `StrEnum` → HTTP 境界と UseCase で型安全に使い、Repository が DB マッピングを担当
- 関心の分離がより明確

**本番投入可能性**: 問題なし。`StrEnum` は SQLAlchemy の `Enum` 型と組み合わせると完璧。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [ ] 状態遷移が `transition_task()` のように集約されているか（散在した `if status == "done":` を禁止）
- [ ] `Flag` の権限チェックで `perm == Permission.READ`（完全一致）でなく `Permission.READ in perm`（部分一致）を使っているか
- [ ] `IntEnum` の算術演算結果が `int` になることをコードが前提にしていないか
- [ ] Enum メンバーを文字列比較（`status == "pending"`）でなく Enum 比較（`status == TaskStatus.PENDING`）しているか
- [ ] DB に保存する Enum 値は `.value` を使って保存し、読み出し時に Enum に変換しているか

**チームでの安全なパターン**: 状態遷移グラフは `dict[Status, set[Status]]` で明示的に宣言し、
UseCase の外部に公開する（テストしやすくなる）。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高

**「初心者でも安全な API」達成度**: 高
- Pydantic + `StrEnum` の組み合わせにより、HTTP 境界での自動バリデーションが確立される
- 無効な状態値は 422 で自動的に拒否される

**設計上の負債・ドキュメント不足**:
- nene2 の example ドメイン（Note / Tag / Comment）に `StrEnum` を使っているフィールドがない
- Note の `status` フィールドに `StrEnum` を導入するサンプルがあると良い

**Follow-up Issue 候補**: `docs: StrEnum を使ったドメイン状態管理の how-to を追加`

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | `docs: StrEnum + Pydantic + 状態遷移パターンの how-to を追加` | docs |
| 低 | `feat: example/note に status フィールド（StrEnum）を追加してパターンを実演` | feat |

---

## まとめ

`enum` モジュールは nene2-python のドメインモデル設計に直接適用できる重要な機能。
`StrEnum` + Pydantic v2 の組み合わせで HTTP 境界の自動バリデーションが完成し、
`Flag` による権限管理は RBAC の実装基盤になる。
32 テスト全通過、摩擦ゼロ。
状態遷移を `dict[Status, set[Status]]` で宣言するパターンは UseCase 内で採用が推奨される。
