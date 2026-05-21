# FT172: dataclasses モジュール

**日付**: 2026-05-21
**テーマ**: `dataclasses` モジュール — `dataclass`・`field()`・`__post_init__`・`asdict`・`frozen=True`/`slots=True`
**セキュリティ診断**: なし（172 % 3 = 1）
**クラッカーペンテスト**: **あり**（FT172, 176, 180... の4回毎ペンテストサイクル開始）

---

## 概要

Python 標準ライブラリの `dataclasses` モジュールを nene2-python フレームワーク上で検証した。
`dataclasses` は CLAUDE.md で `dataclass(frozen=True, slots=True)` が
「イミュータブル値オブジェクト」のパターンとして明示されており、
nene2 の Entity / ValueObject 実装の中核。
FT172 は4回毎クラッカーペンテストの最初のサイクルで、
実際に攻撃ペイロードを送り込んでエンドポイントの耐性を確認した。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft172-dataclasses/`

### 主要機能

| クラス/関数 | 概要 |
|---|---|
| `Point` (dataclass) | 可変な2D座標。`distance_to()` メソッド付き |
| `NoteId` (frozen, slots) | 正の整数のみ許容する値オブジェクト。`__post_init__` で検証 |
| `Money` (frozen, slots) | amount (≥0) + currency (3文字)。`add()` で同通貨のみ加算 |
| `Note` (frozen, slots) | title (非空・200文字以下) + content + tags (tuple) + priority (1-5) |
| `Tag` | `field(default_factory=list)` で独立したリストを各インスタンスに持つ |
| `NoteEntity` | `Entity` を継承し `__post_init__` で `super().__post_init__()` を呼ぶ |
| `UniqueResource` | `eq=False` でカスタム等値比較。`_id` フィールドを `init=False` で生成 |
| `asdict()` / `astuple()` / `replace()` | 変換・イミュータブルコピー |
| `fields()` / `get_field_metadata()` | リフレクション |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/dataclasses/point` | Point 間の距離計算 |
| POST | `/dataclasses/money` | Money バリューオブジェクト生成 |
| POST | `/dataclasses/money/add` | 2 つの Money を加算 |
| POST | `/dataclasses/note` | Note 作成（__post_init__ バリデーション） |
| POST | `/dataclasses/note/update-title` | replace() で frozen Note を更新 |
| GET | `/dataclasses/note/tuple` | astuple() での変換 |
| POST | `/dataclasses/tag` | Tag 作成（default_factory 確認） |
| GET | `/dataclasses/note-id` | NoteId バリューオブジェクト生成 |
| GET | `/dataclasses/fields/note` | fields() リフレクション |
| POST | `/dataclasses/entity` | NoteEntity 継承確認 |

---

## テスト結果

**35 passed（摩擦ゼロ）**

```
35 passed in 0.82s
```

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

---

## 観察点

### 観察1: `frozen=True, slots=True` の組み合わせが nene2 の標準値オブジェクトパターン

```python
@dataclass(frozen=True, slots=True)
class Money:
    amount: int
    currency: str = "JPY"
```

`frozen=True` でハッシュ可能・辞書キー使用可能・誤った変更を防ぐ。
`slots=True` でメモリ効率化（`__dict__` なし）。
両方セットが nene2 の推奨。`__post_init__` でビジネスルールを強制できる。

### 観察2: `field(default_factory=list)` は各インスタンスに独立したリストを作る

```python
@dataclass
class Tag:
    aliases: list[str] = field(default_factory=list)
```

`aliases: list[str] = []` と書くとすべてのインスタンスが同じリストを共有してしまう
（Python の有名な罠）。`field(default_factory=list)` が正しいパターン。
`frozen=True` な dataclass では `tuple` を使うことでこの問題を回避できる。

### 観察3: `replace()` で frozen dataclass を「コピーして一部変更」できる

```python
updated = replace(note, title="New Title")
```

`frozen=True` は直接代入を禁止するが `replace()` で新しいインスタンスを生成できる。
UseCase 内でドメインオブジェクトを更新するパターンに使える。

### 観察4: 継承 dataclass では `super().__post_init__()` を明示的に呼ぶ

```python
@dataclass(frozen=True, slots=True)
class NoteEntity(Entity):
    def __post_init__(self) -> None:
        super().__post_init__()  # Entity の検証を実行
        if not self.title.strip():
            raise ValueError("title cannot be empty")
```

Python の dataclass 継承では `__post_init__` の呼び出しチェーンは自動化されない。
`super().__post_init__()` を書かないと親クラスのバリデーションがスキップされる。
ruff / mypy ではこのミスを検出できないため、コードレビューチェックポイントが必要。

### 観察5: `field(metadata=...)` でフィールドにメタデータを付与できる

```python
priority: int = field(default=1, metadata={"min": 1, "max": 5})
```

`metadata` はイミュータブルな `MappingProxyType` として保存される。
`fields(Note)` で取得でき、バリデーション設定・OpenAPI スキーマ生成・デバッグツールに活用できる。

---

## nene2-python フレームワークとの統合

- `Note`, `Tag`, `Comment` エンティティはすべて `dataclass(frozen=True, slots=True)` で実装すべき（現状の実装と一致）
- `__post_init__` のビジネスルールは UseCase の入力検証と分離 — ドメイン不変条件は Entity が責任を持つ
- `replace()` パターンは UseCase の「更新」操作を副作用なしに実装するための標準手法
- `asdict()` は JSON レスポンス・DB 保存の前処理として使える（ただし nested dataclass も展開される点に注意）

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`@dataclass` は `class` の boilerplate（`__init__`・`__repr__`・`__eq__`）を自動化する機能として直感的に理解できる。
`frozen=True` の「変更できない」制約は最初は不便に感じるが、イミュータブリティの価値を説明すると受け入れる。

**ドキュメント理解**: `field(default_factory=list)` が必要な理由（同一リスト共有の罠）は
一度ハマらないと気づかない。nene2 の examples でこのパターンを明示すると良い。

**事故リスク**: 中。`frozen=True` なしの dataclass にグローバルから書き込むと副作用が発生する。
nene2 の「すべて frozen」規約が守られていれば事故率は低い。

**規約の使いやすさ**: `@dataclass(frozen=True, slots=True)` + `__post_init__` のパターンはコピペで使える。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`replace()` を知らずに `note.title = "new"` を試みて `FrozenInstanceError` で止まる。
エラーメッセージから解決策を探すが `replace()` にたどり着くのに時間がかかる。

**コピペ可能性**: 中。`replace()` は知らなければ思いつかない。ドキュメントが必要。

**拡張時の罠**: 継承 dataclass で `super().__post_init__()` を忘れる。
親クラスの検証がスキップされることに気づかず本番に出る可能性。

**セキュリティ的な事故リスク**: 中（ペンテストで発見した float overflow 参照）。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `readonly` interface と `frozen dataclass` が概念的に対応する。
`asdict()` は TypeScript の `toJSON()` に相当。

**事故リスク**: 低。概念の対応関係が作れる。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `Model` クラスと nene2 の `dataclass` は役割が異なる。
Django Model は DB 操作まで含むが、nene2 の dataclass は純粋なドメインオブジェクト。
リポジトリパターンで分離されているため、モデル変更が DB に直結しない設計が明確。

**本番投入可能性**: 問題なし。ただし float フィールドの `nan`/`inf` 対策が必要（ペンテスト結果参照）。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [ ] 継承 dataclass で `super().__post_init__()` を呼んでいるか
- [ ] `field(default=list)` でなく `field(default_factory=list)` を使っているか
- [ ] `float` フィールドに `nan`/`inf` が入った場合の動作を確認しているか（ペンテスト E4 参照）
- [ ] `asdict()` を JSON レスポンスに使う場合、nested dataclass が再帰的に展開されることを理解しているか
- [ ] `__post_init__` のバリデーションエラーが API 側で適切にハンドリングされているか

**チームでの安全なパターン**: `float` フィールドを含む dataclass は Pydantic の `Field(allow_inf_nan=False)` または
`__post_init__` で `math.isfinite()` チェックを追加する規約を設ける。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高

**「初心者でも安全な API」達成度**: 中
- `__post_init__` バリデーションは HTTP 境界の Pydantic より後で実行される二重チェックで安全
- ただし float フィールドの `nan`/`inf` は両方の層をすり抜ける（ペンテスト参照）

**設計上の負債**:
- Pydantic の `float` フィールドは `nan`/`inf` を許容するため、`math.isfinite()` チェックが必要
- CLAUDE.md に「float フィールドには `math.isfinite()` 確認必須」の規約が未記載

---

## クラッカーペンテスト（FT172 — 4回毎の第1回）

> **実施方針**: チェックリストではなく、実際に攻撃ペイロードを送り込んで耐えられるかを試験する。
> クラッカーは公開 API の仕様から内部構造を推測し、想定外の入力で動作を崩そうとする。

### フェーズ1: 構造推測（攻撃者の視点）

`GET /openapi.json` から推測できる内部構造:
- `MoneyBody: {amount, currency}` → 内部に `Money(amount, currency)` の dataclass が存在する
- `NoteBody: {title, content, tags, priority}` → `__post_init__` でバリデーションがある可能性
- `amount: int, ge=0` → 0 は許容、負の数は Pydantic でブロック
- `currency: str, min_length=3, max_length=3` → 固定長の文字列、文字種は制限なし（推測）

エラーメッセージから漏洩した内部情報:
- `{"type": "greater_than_equal", "loc": ["body", "amount"]}` → Pydantic v2 の構造が判明
- `Note title cannot be empty` → `__post_init__` のエラーメッセージがそのまま漏洩
- `ValueError` の内容がそのまま `{"error": "..."}` として公開される

### フェーズ2: 攻撃実行ログ

#### A. Pydantic バイパス攻撃

| ペイロード | 結果 | 判定 |
|---|---|---|
| `amount: "1000"` (str→int) | 200 OK、`amount: 1000` に変換 | ⚠️ 型強制（設計上許容） |
| extra fields: `is_admin: true` | 201 OK、extra は無視 | ✅ 耐えた |
| `title: null` | 422 | ✅ 耐えた |
| `priority: 0` (ge=1 境界外) | 422 | ✅ 耐えた |
| `priority: 2^31` | 422 | ✅ 耐えた |
| `amount: 1.9` (float→int) | 422（ge=0 通過後に精度エラー） | ✅ 耐えた |

**注記**: Pydantic v2 は `"1000"` を `int` に型強制する。セキュリティ上の問題ではないが、
型安全を重視する場合は `ConfigDict(strict=True)` が必要。

#### B. ビジネスロジック攻撃

| ペイロード | 結果 | 判定 |
|---|---|---|
| `title: "\t\n  "` (空白のみ) | 422 (`Note title cannot be empty`) | ✅ 耐えた |
| `currency: "JP"` (2文字) | 422 (Pydantic min_length) | ✅ 耐えた |
| `currency: "JPYY"` (4文字) | 422 (Pydantic max_length) | ✅ 耐えた |
| `currency: "<sc"` (HTML文字) | **200 OK、`<sc` がそのまま返る** | ⚠️ 弱点（後述） |
| `currency: "';-"` (SQL文字) | **200 OK、`';-` がそのまま返る** | ⚠️ 弱点（後述） |

**⚠️ B4 弱点: currency フィールドは文字種チェックなし**  
3文字の長さ制限のみで、HTML/SQL の特殊文字が通過する。
FT172 は JSON API のため XSS は直接発生しないが、もし通貨コードがログ・メール・HTMLに埋め込まれると問題になる。
ISO 4217 コード（`[A-Z]{3}`）のみ許容するバリデーションが推奨。

#### C. 境界値/エッジケース攻撃

| ペイロード | 結果 | 判定 |
|---|---|---|
| `title: "hello\x00world"` (null バイト) | **201 OK、null バイトが保存される** | ⚠️ 弱点（後述） |
| `title: "a" * 200` (境界ちょうど) | 201 OK | ✅ 耐えた |
| `title: "a" * 201` (境界+1) | 422 | ✅ 耐えた |
| RTL オーバーライド文字 U+202E | **201 OK、そのまま保存** | ⚠️ 弱点（後述） |
| Unicode NFC vs NFD | 両方 201 OK（正規化なし） | ⚠️ 注意 |
| 21 tags (max=20) | 422 | ✅ 耐えた |

**⚠️ C1 弱点: null バイトがタイトルに保存される**  
`"hello\x00world"` が `201 OK` で保存される。
Python の文字列操作では無害だが、このタイトルを C ライブラリ・ファイルパス・DBに渡すと
null バイト以降が切り捨てられる（null バイトインジェクション）。
`__post_init__` に `"\x00" in self.title` チェックが必要。

**⚠️ C4 弱点: RTL オーバーライド文字が保存される**  
`U+202E` (RIGHT-TO-LEFT OVERRIDE) がタイトルに保存される。
ファイルダウンロード機能でタイトルがファイル名に使われると `safe‮evil.exe` が `safeexe.evil` に見える。
テキスト表示のみの場合は低リスクだが、ファイル名利用時は危険。

#### D. 情報収集攻撃

| ペイロード | 結果 | 判定 |
|---|---|---|
| `GET /dataclasses/admin` | 404 Not Found | ✅ 耐えた |
| 不正 JSON | 422 `{"detail": [...]}` | ✅ スタックトレース非公開 |
| `amount: -999` のエラー | `{"detail": [{"type": "greater_than_equal", ...}]}` | ⚠️ Pydantic の内部型情報が漏洩 |
| `GET /docs` | **200 OK** | ⚠️ 本番では無効化が必要 |

**⚠️ D3 弱点: Pydantic のエラーレスポンスに内部型情報が含まれる**  
`"type": "greater_than_equal"` というフィールド名が漏洩する。
FT172 はサンドボックスのため許容するが、本番 API では Pydantic エラーを nene2 の
Problem Details 形式に変換してフィールド名を抽象化する必要がある。

#### E. DoS 試み

| ペイロード | 結果 | 判定 |
|---|---|---|
| 1000 tags (max=20) | 422 | ✅ 耐えた |
| content=10000 chars (max=5000) | 422 | ✅ 耐えた |
| 1000 aliases (max=10) | 422 | ✅ 耐えた |
| **`x: Infinity` の raw JSON** | **500 Internal Server Error** | ❌ **突破！** |
| `x: 1e308` | **500 Internal Server Error** | ❌ **突破！** |

**❌ E4 重大発見: float オーバーフローで 500 が返る（DoS 脆弱性）**

```
POST /dataclasses/point {"x": 1e308, "y": 0}
→ OverflowError: Numerical result out of range
→ 500 Internal Server Error
```

攻撃手順:
1. Pydantic の `float` フィールドは `1e308` を受け入れる（有効な float）
2. `distance_to()` で `(1e308 - 0) ** 2` が計算され `OverflowError` が発生
3. `ErrorHandlerMiddleware` が `OverflowError` を捕捉して 500 を返す
4. クライアントは繰り返し 500 を引き起こしてサービスを不安定化できる

**影響**: 任意のクライアントが `/dataclasses/point` に `{"x": 1e308}` を連続送信すると
サーバーが毎回 500 エラーを返す。直接クラッシュはしないが、ログが汚染され
異常検知システムが誤反応する可能性がある。

**修正方法**:
```python
# Pydantic フィールドで制限
x: float = Field(gt=-1e100, lt=1e100)  # 現実的な上下限

# または __post_init__ で
import math
def __post_init__(self) -> None:
    if not (math.isfinite(self.x) and math.isfinite(self.y)):
        raise ValueError("Coordinates must be finite")
```

### フェーズ3: 攻撃まとめ

| 攻撃カテゴリ | 試みた攻撃数 | 突破 | 耐えた | 弱点発見 |
|---|---|---|---|---|
| Pydantic バイパス | 6 | 0 | 6 | 型強制（許容） |
| ビジネスロジック | 5 | 0 | 3 | 2（特殊文字） |
| 境界値/エッジ | 7 | 0 | 4 | 3（null/RTL/Unicode） |
| 情報収集 | 4 | 0 | 3 | 1（Pydantic 型情報） |
| DoS | 5 | **2** | 3 | **float overflow → 500** |

**攻撃耐性評価**: 軽微な問題あり（float overflow は要修正）  
**発見した弱点**:
1. **HIGH**: `float` フィールドへの `inf`/`1e308` で `OverflowError` → 500（DoS）
2. **MEDIUM**: currency フィールドの文字種チェックなし（HTML/SQL 特殊文字が通過）
3. **LOW**: null バイトがタイトルに保存可能
4. **LOW**: RTL オーバーライド文字がタイトルに保存可能
5. **INFO**: Pydantic のエラーレスポンスに内部型情報が含まれる
6. **INFO**: `/docs` が本番相当の環境でも公開されている

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 高 | `fix: float フィールドに math.isfinite() ガードを追加（OverflowError DoS 対策）` | fix |
| 高 | `docs: CLAUDE.md に float フィールドのバリデーション要件（isfinite チェック）を追記` | docs |
| 中 | `fix: currency フィールドに ISO 4217 形式（[A-Z]{3}）バリデーションを追加` | fix |
| 中 | `docs: null バイト・RTL 文字の __post_init__ チェックパターンを how-to に追加` | docs |
| 低 | `feat: Pydantic ValidationError を nene2 Problem Details に変換して型情報を抽象化` | feat |

---

## まとめ

`dataclasses` モジュールは nene2-python の Entity / ValueObject 設計に直結する重要な機能。
35 テスト全通過、摩擦ゼロ。

**クラッカーペンテストの主な発見**: `float` フィールドへの `1e308` / `Infinity` 送信で
`OverflowError` が発生し 500 が返る（DoS 脆弱性）。
Pydantic の `float` 型は `inf`・`nan`・`1e308` を有効な値として受け入れるが、
演算時に `OverflowError` が発生する。
`math.isfinite()` または `Field(gt=-1e100, lt=1e100)` による対策が必要。

通貨コードの文字種チェック不足・null バイト通過・RTL オーバーライド文字の保存は
今後の how-to で対応パターンを記録する。

