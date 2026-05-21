# FT169: typing モジュール

**日付**: 2026-05-21
**テーマ**: `typing` モジュール — `TypedDict`・`Protocol`・`overload`・`Literal`・`TypeGuard`・`Required`/`NotRequired`
**セキュリティ診断**: なし（169 % 3 = 2）

---

## 概要

Python 標準ライブラリの `typing` モジュール（Python 3.12+ の先進的な機能を含む）を
nene2-python フレームワーク上で検証した。
`typing` は nene2 の「strict typing」設計哲学の根幹であり、
HTTP 境界の型安全性・ドメインモデルの不変性・プロトコルによる構造的サブタイピングを
支える重要モジュール。
CLAUDE.md の型安全ポリシー（`Any` 禁止・`TypedDict`・`Protocol` 活用）に直接対応する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft169-typing/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `NoteDict` (TypedDict) | 構造化辞書の型定義。`id`, `title`, `content` |
| `NoteCreateDict` (TypedDict) | `NotRequired[str]` でオプショナルフィールドを表現 |
| `NoteWithMetaDict` (TypedDict 継承) | `total=False` でオプショナル拡張フィールドを追加 |
| `Serializable` (Protocol) | `@runtime_checkable` で `isinstance()` チェック可能な構造的サブタイプ |
| `Closeable` (Protocol) | `close()` を持つリソースのプロトコル |
| `parse_id()` (@overload) | `str` 引数 → `int \| None`、`int` 引数 → `int` の型多態性 |
| `double()` (@overload) | `int` / `str` / `float` それぞれに異なる戻り値型 |
| `SortOrder` / `NoteStatus` / `HttpStatusCode` (Literal) | `type` エイリアス + `Literal` で定数列挙 |
| `is_note_dict()` (TypeGuard) | 実行時の型絞り込み関数 |
| `build_search_params()` | `Required` / `NotRequired` を持つ `SearchQuery` TypedDict の利用例 |
| `inspect_hints()` | `get_type_hints()` で実行時にクラスメソッドの型情報を取得 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/typing/notes` | TypedDict でノートを作成 |
| GET | `/typing/notes` | Literal `SortOrder` でノートをソート |
| POST | `/typing/notes/tags` | TypedDict 継承でタグを追加 |
| GET | `/typing/parse-id` | @overload — 文字列 → int 変換 |
| GET | `/typing/double` | @overload — 型別の倍返し |
| POST | `/typing/search` | Required/NotRequired を持つ SearchQuery |
| GET | `/typing/type-guard` | TypeGuard で型絞り込み |
| GET | `/typing/protocol` | Protocol + is_serializable() |
| POST | `/typing/close-resources` | Closeable Protocol でリソース管理 |
| GET | `/typing/hints` | get_type_hints() でクラスのヒント取得 |
| GET | `/typing/filter-status` | Literal[NoteStatus] でフィルタリング |
| GET | `/typing/response` | Literal[HttpStatusCode] でレスポンス生成 |

---

## テスト結果

**45 passed（摩擦ゼロ）**

```
45 passed in 0.86s
```

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

---

## 観察点

### 観察1: `type` エイリアス構文（Python 3.12+）で `Literal` を名前付き型にできる

```python
type SortOrder = Literal["asc", "desc"]
type NoteStatus = Literal["draft", "published", "archived"]
type HttpStatusCode = Literal[200, 201, 204, 400, 401, 403, 404, 422, 500]
```

Python 3.12 の `type` ステートメントを使うと、`Literal` に意味のある名前がつく。
`TypeAlias` アノテーション（旧形式）より明示的で mypy --strict に通る。
定数の列挙は Enum でなく Literal + type エイリアスが軽量な代替になる。

### 観察2: `TypedDict` + `NotRequired` で HTTP BodyModel の代替が作れる

```python
class NoteCreateDict(TypedDict):
    title: str
    content: NotRequired[str]  # 省略可能
```

Pydantic BaseModel が必要な HTTP 境界では引き続き Pydantic を使うが、
UseCase 内部のデータ構造・関数の引数・レポジトリの返り値には
`TypedDict` が軽量で mypy に完全対応する。
`total=False` よりも `NotRequired` を使う方が、どのフィールドが省略可能かが明確。

### 観察3: `@runtime_checkable Protocol` で `isinstance()` による構造的型チェックが可能

```python
@runtime_checkable
class Serializable(Protocol):
    def to_dict(self) -> dict[str, object]: ...

note = InMemoryNote(1, "Test")
assert isinstance(note, Serializable)  # True — クラス継承不要
```

`InMemoryNote` は `Serializable` を継承していないが、`to_dict()` を持つため
`isinstance()` が `True` を返す。
nene2 のリポジトリパターンで「`to_dict()` を持つドメインオブジェクトなら何でも受け付ける」
関数を書くときに有効。ただし `@runtime_checkable` はメソッドの「存在」しか確認せず、
引数・戻り値型の一致は確認しない。

### 観察4: `@overload` で引数の型による戻り値型の分岐を型安全に表現できる

```python
@overload
def parse_id(value: str) -> int | None: ...
@overload
def parse_id(value: int) -> int: ...

def parse_id(value: str | int) -> int | None:
    ...
```

`parse_id(42)` のとき mypy は戻り値を `int`（`None` なし）と判断し、
`parse_id("foo")` のとき `int | None` と判断する。
`None` チェックを呼び出し側で毎回書く必要がなくなる箇所で効果的。

### 観察5: `TypeGuard` で `Any` 型の辞書を型安全に絞り込める

```python
def is_note_dict(obj: object) -> TypeGuard[NoteDict]:
    if not isinstance(obj, dict):
        return False
    return (
        isinstance(obj.get("id"), int)
        and isinstance(obj.get("title"), str)
        and isinstance(obj.get("content"), str)
    )

def process_unknown(data: Any) -> str:
    if is_note_dict(data):
        return note_summary(data)  # mypy はここで data を NoteDict として扱う
```

外部 JSON・DB 生クエリ結果など `Any` 型を安全に使う唯一の公式手段。
`cast()` は「信頼してキャスト」するだけだが、`TypeGuard` は実行時チェックと型絞り込みを両立する。

---

## nene2-python フレームワークとの統合

- `TypedDict` は nene2 の UseCase Input/Output DTO の軽量代替として使える（Pydantic より軽い）
- `Protocol` は `RepositoryInterface` の ABC 代替として `NoteRepositoryProtocol` を定義するのに有効
- `Literal` は nene2 の `SortOrder` / `DB_ADAPTER` 等の設定値型に直接適用できる
- `TypeGuard` は `/notes` 一覧取得の外部データを型安全に絞り込む Use Case で使える
- CLAUDE.md の「`Any` 禁止 / `TypedDict` で Dict 構造を型付け」ポリシーと完全に整合

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`TypedDict` は `class` で辞書を型定義する概念が新しく、
「Pydantic の `BaseModel` と何が違うの？」という混乱が起きる。

**ドキュメント理解**: nene2 how-to に「HTTP 境界は Pydantic・UseCase 内部は TypedDict」の
使い分けガイドがあれば即解決する。現時点では CLAUDE.md を読み込まないと判断できない。

**事故リスク**: 低。`TypedDict` の誤用は実行時エラーにはならず、mypy が検出してくれる。
ただし mypy なしで開発すると TypedDict の型安全の恩恵がゼロになる。

**規約の使いやすさ**: `NoteDict(TypedDict)` のパターンはコピペで書ける。
`total=False` と `NotRequired` の使い分けは最初は迷う。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`Protocol` を「インターフェース」として理解できるが、
`@runtime_checkable` の「struct subtyping = 継承不要」は最初は驚く。
「実行してみたら通った」という体験で理解が定着する。

**コピペ可能性**: 高。`@runtime_checkable class Xxx(Protocol)` はテンプレートとして使える。

**拡張時の罠**: `@runtime_checkable Protocol` はメソッドの引数・戻り値型を確認しない。
`to_dict() -> dict[str, object]` を `to_dict() -> str` に変えても `isinstance()` は `True` を返す。
実行時の型安全は Protocol の責務ではなく、mypy の責務であることを理解が必要。

**セキュリティ的な事故リスク**: 低。typing の誤用がセキュリティインシデントに直結するケースは稀。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `interface` / `type` / `as const` との対応関係が作れる。
- TS の `interface` → Python の `TypedDict`（完全対応）
- TS の `as const` 配列 → Python の `Literal`（概念的に近い）
- TS の `function overloads` → Python の `@overload`（ほぼ同じ）
- TS の `type predicate` (`is`) → Python の `TypeGuard`（同等）

**エラーレスポンスの質**: 型ミスマッチは mypy が捕捉し、HTTP 境界では Pydantic が 422 を返す。
フロントエンド開発者にとって馴染みのある体験。

**事故リスク**: 低。TS の型システムの経験が直接活かせる。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `TypedDict` 活用は限定的（Django は dict よりモデルクラスを使う傾向）。
FastAPI ユーザーにとっては Pydantic v2 が `TypedDict` をスキーマとして受け付けるため、
境界が曖昧になりやすい。

**他フレームワークとの差異**:
- Django: ドメインは Model クラスで表現、typing との組み合わせは発展途上
- nene2: TypedDict（UseCase 内部）+ Pydantic（HTTP 境界）の明確な使い分けが nene2 の差別化

**本番投入可能性**: 問題なし。`@overload` / `TypeGuard` は FastAPI ルーターとも問題なく共存する。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [ ] `TypedDict` フィールドに `NotRequired` を使って省略可能性を明示しているか（`total=False` は非推奨）
- [ ] `@runtime_checkable Protocol` を型安全の唯一の砦にしていないか（mypy でも確認必須）
- [ ] `@overload` の実装本体に型注釈が適切についているか（オーバーロードシグネチャのみ書いて本体を忘れるミス）
- [ ] `TypeGuard` 関数が実行時チェック（isinstance 等）を実施しているか（`return True` のみは危険）
- [ ] `cast()` には `# reason:` コメントがついているか（CLAUDE.md ポリシー）

**チームでの安全なパターン**: `TypedDict` は UseCase I/O の DTO として標準化し、
HTTP 境界は Pydantic、内部は TypedDict という二層構造を CLAUDE.md に明記する。

**ツール追加の必要性**: `mypy --strict` で `TypedDict` の型チェックが網羅されるため追加不要。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高

**「初心者でも安全な API」達成度**: 高
- `TypedDict` + mypy の組み合わせで、実行前に型エラーが検出される
- `TypeGuard` で `Any` 由来のデータを安全に絞り込める

**設計上の負債・ドキュメント不足**:
- CLAUDE.md の「TypedDict で Dict 構造を型付け」ポリシーは記載あるが、Pydantic との使い分けが未記載
- nene2 の UseCase Input/Output は `dataclass(frozen=True)` で実装されているが、
  `TypedDict` が適切な場面（JSON 応答の直接マッピング等）も存在する

**Follow-up Issue 候補**: `docs: TypedDict vs Pydantic vs dataclass の使い分けガイドを how-to に追加`

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | `docs: TypedDict vs Pydantic vs dataclass の使い分けガイドを how-to に追加` | docs |
| 低 | `feat: NoteRepositoryProtocol を TypedDict + Protocol で再実装するサンプルを追加` | feat |

---

## まとめ

`typing` モジュールは nene2-python の型安全設計の根幹をなす機能群。
45 テスト全通過、摩擦ゼロ。

`TypedDict` + `NotRequired` は UseCase 内部データ構造の軽量 DTO として直接使える。
`Protocol` + `@runtime_checkable` は nene2 の `RepositoryInterface` の ABC 代替として有効で、
継承なしの構造的サブタイピングを実現する。
`TypeGuard` は `Any` 型データを型安全に絞り込む唯一の公式手段で、外部データ処理に必須。
Python 3.12 の `type X = Literal[...]` 構文で定数列挙が軽量に書ける。

