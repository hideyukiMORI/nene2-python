# FT213: abc モジュール — ABC / abstractmethod / register / __subclasshook__

**日付**: 2026-05-22
**テーマ**: Python `abc` モジュールの ABC / abstractmethod / register / __subclasshook__ の実装と検証
**セキュリティ診断**: あり（213 % 3 = 0）
**クラッカーペンテスト**: なし（213 % 4 = 1）

---

## 概要

`abc` モジュールは Python の抽象基底クラス（Abstract Base Class）機能を提供する。今 FT では 4 つの主要機能を検証した。

| API | ユースケース |
|---|---|
| `ABC` + `abstractmethod` | 具象実装を強制する抽象基底クラス |
| `@final` | サブクラスによるオーバーライドを禁止するメソッド |
| `register()` | 継承なしで仮想サブクラスを登録（既存クラスへの後付け適用） |
| `__subclasshook__` | hasattr ベースの構造的サブタイピング |
| `__abstractmethods__` | 実行時の抽象メソッド一覧イントロスペクション |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft213-abc/`

### 主要機能

| クラス/関数 | 概要 |
|---|---|
| `ShapeInterface(ABC)` | `area` / `perimeter` を abstractmethod として定義。`__subclasshook__` で hasattr ベースの構造的認識 |
| `Circle`, `Rectangle` | `ShapeInterface` の具象実装。`frozen=True, slots=True` + `__post_init__` バリデーション |
| `LegacyPolygon` | 継承なし。`ShapeInterface.register()` で仮想サブクラス登録 |
| `FormatterInterface(ABC)` | `format_entry` を abstractmethod、`format_all` を `@final` で定義 |
| `KeyValueFormatter`, `MarkdownTableFormatter` | `FormatterInterface` の具象実装 |
| `get_abstract_methods()` | `__abstractmethods__` 属性を読み取って抽象メソッド一覧を返す |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/abc/circle` | Circle の面積・周長計算（`abstractmethod` 実装確認） |
| POST | `/abc/rectangle` | Rectangle の面積・周長計算 |
| POST | `/abc/register` | `register()` で登録した仮想サブクラスの isinstance / issubclass 確認 |
| POST | `/abc/format` | FormatterInterface の具体実装でテキスト整形 |
| POST | `/abc/abstract-methods` | `__abstractmethods__` の実行時イントロスペクション |

---

## 摩擦点

### F-1: `__subclasshook__` の戻り値型と mypy `no-any-return`

**観察**: Python ドキュメントの標準パターンでは `__subclasshook__` は `bool | NotImplementedType` を返す。

```python
@classmethod
def __subclasshook__(cls, subclass: type) -> bool | NotImplementedType:
    if cls is ShapeInterface:
        return hasattr(subclass, "area") and hasattr(subclass, "perimeter")
    return NotImplemented
```

しかし mypy --strict は `NotImplementedType` のインポートが曖昧であり、かつ `__subclasshook__` のオーバーライド型シグネチャが `bool` を要求するため `no-any-return` エラーになる。

**対処**: 常に `bool` を返すよう単純化した。

```python
@classmethod
def __subclasshook__(cls, subclass: type) -> bool:
    return hasattr(subclass, "area") and hasattr(subclass, "perimeter")
```

これによりサブクラスが `cls is ShapeInterface` を見て `NotImplemented` にフォールバックする機会を失うが、今 FT のデモ目的では許容範囲。mypy 側の `__subclasshook__` 型サポートが改善されるまでの回避策。

---

### F-2（HIGH）: `Infinity`/`NaN` 非標準 JSON がエラーシリアライザーを 500 クラッシュさせる

**発見**: セキュリティ診断で発見。非標準 JSON ボディを直接バイト列で送信した場合:

```
POST /abc/circle
Content-Type: application/json
Body: {"radius": Infinity}
```

**挙動連鎖**:
1. Python 3.14 の JSON パーサーが `Infinity` を `float('inf')` として受け入れる（JSON spec 違反だが Python が許容）
2. Pydantic の `gt=0, le=MAX_DIMENSION` バリデーションが `inf` に対して False → `RequestValidationError` を発生
3. FastAPI のデフォルト `RequestValidationError` ハンドラーが `jsonable_encoder(exc.errors())` を呼ぶ
4. エラー詳細に `{'input': inf}` が含まれ、`json.dumps(inf)` が `ValueError: Out of range float values are not JSON compliant` で失敗
5. **結果: 422 ではなく 500** → DoS ベクター

**修正**: カスタム `RequestValidationError` ハンドラーを登録し、`_sanitize_value()` で非有限 float を文字列 `"inf"`/`"nan"` に変換してから 422 を返す。

```python
def _sanitize_value(value: object) -> object:
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value

@application.exception_handler(RequestValidationError)
async def _safe_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    sanitized = [_sanitize_value(err) for err in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": sanitized})
```

**根本対策**: FT212 と同一の問題。nene2 の `ErrorHandlerMiddleware` または `RequestValidationError` ハンドラーを標準化して非有限 float をサニタイズすべき（Issue #594 参照）。

---

## セキュリティ診断結果

| カテゴリ | 項目 | 結果 |
|---|---|---|
| Mass Assignment | 余分なフィールドを含むリクエスト | 無害（Pydantic が無視） |
| 入力バリデーション | `max_length=500` の値フィールド超過 | 422（`_BoundedStr` で遮断） |
| 入力バリデーション | dict キー数 > 100 | 422 |
| 入力バリデーション | dict キー数 = 0 | 422（空辞書チェック） |
| 入力バリデーション | 未知の formatter 名 | 422（`Literal` 型で遮断） |
| 入力バリデーション | 未知の class_name | 422（`Literal` 型 + ValueError → 422） |
| Unicode RTL | class_name に RTL 文字を含む | 422（`Literal` 型が完全一致） |
| 非有限 float | `Infinity` を非標準 JSON で送信 | **修正済み (F-2)** → 422 |
| 非有限 float | `NaN` を非標準 JSON で送信 | **修正済み (F-2)** → 422 |
| 情報漏洩 | 必須フィールド欠落時のスタックトレース露出 | なし（422 の detail のみ） |
| dict キー長 | 1000 文字のキー | 200（キー長制限なし — 低リスク）|

**キー長無制限について**: `/abc/format` の `data` dict のキーに対して最大長制限がない。`_BoundedStr` は値のみを制約し、キーは任意長を受け入れる。ただし Pydantic の通常の JSON デシリアライズで極端に長いキーが到達することはまれであり、実用上の脅威は低い。

**総合評価: 条件付き合格**（F-2 修正後）

---

## テスト結果

```
30 passed in 0.40s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

ABC と abstractmethod は「実装しなければならないメソッドを定義する仕組み」として直感的に理解できる。`register()` の「継承せずに仲間として認識させる」概念は初見では分かりにくいが、`LegacyPolygon` の例を見れば「既存コードへの後付け適用」として理解できる。

**ドキュメント理解**: `isinstance(polygon, ShapeInterface)` が `True` になるのに `ShapeInterface in LegacyPolygon.__mro__` が `False` という結果は驚きを生む。この仕組みが「仮想サブクラス」という概念の核心であることを明示すると理解しやすい。

**事故リスク（中）**: `abstractmethod` を持つクラスをインスタンス化しようとすると `TypeError` が発生するが、エラーメッセージ「Can't instantiate abstract class ... with abstract method ...」は初心者にも分かりやすい。

**規約の使いやすさ**: `/abc/abstract-methods` エンドポイントで実際に `is_abstract: false` が返ることで「全 abstractmethod を実装した」の確認ができるのは教育的。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`ABC + abstractmethod` はよく知っているが `__subclasshook__` の使いどころは知らない人が多い。`hasattr` ベースの構造的サブタイピングという概念は「duck typing の静的版」として説明できる。

**コピペ可能性**: `ShapeInterface` + `Circle` / `Rectangle` パターンは、ドメイン層のインターフェースを ABC で定義する標準パターンとしてそのまま使える。

**拡張時の罠**: `@final` を使うと「このメソッドはオーバーライドするな」という意図が型レベルで表現できる。mypy が警告を出すことを知っていれば積極的に使える。

**事故リスク（低）**: Pydantic + `__post_init__` の二重バリデーションで安全。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `interface` + `implements` に相当するが、Python の ABC はクラスを強制するのに対し TS は構造的型付けが主流。`__subclasshook__` が TS の構造的型付けに近い発想。

**エラーレスポンスの質**: 未知の formatter / class_name への 422 が `{field, message, code}` 形式で一貫しており、フロントエンドがエラーを扱いやすい。`Literal` 型を使うことで `code: "invalid_enum_value"` の形式で原因が分かる。

**Python 固有概念**: `register()` による仮想サブクラスは JS/TS には存在しない概念。「型安全でない後方互換の仕組み」として説明すると伝わりやすい。

**事故リスク（低）**: F-2 修正後は 422 を返すため、フロントエンドが適切にエラーを処理できる。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

ABC は Django の `View` や DRF の `BaseSerializer` でおなじみ。`register()` は Django の `Model` クラスが内部で使うパターンと類似している。`__subclasshook__` は Python の collections.abc で広く使われており知識のある人には自然。

**他フレームワークとの差異**: nene2 での ABC の使い方は「リポジトリインターフェース（ABC）と具象実装（InMemory / SQLAlchemy）の分離」に直結している。今 FT のパターンはそのまま `RepositoryInterface` 設計に流用できる。

**nene2 の薄さへの評価**: F-2 の修正が app.py の `create_app()` にカスタムハンドラーを追加する形になっているのは FT212 と同じ問題。Issue #594 で追跡中で、フレームワーク側の修正待ちという整理は適切。

**事故リスク（低）**: 境界値チェックが二重保護で堅牢。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `ABC` を継承した具象クラスが全 abstractmethod を実装しているか（実行時に `TypeError` でなく静的解析で確認）
- `@final` を使っているメソッドを意図せずオーバーライドしていないか（mypy が検出）
- `register()` で登録したクラスが `__abstractmethods__` を実装しているかは実行時チェック不可 — 手動での確認が必要
- `__subclasshook__` を使う場合、`hasattr` チェックだけでは「同名だが実装が異なるメソッド」を許容してしまう可能性がある

**チームでの安全なパターン**: `abstractmethod` + 型注釈の組み合わせは mypy --strict と相性が良く、実装漏れを静的に検出できる。nene2 の標準パターンとして推奨できる。

**事故リスク（低）**: F-2 修正後は全シナリオで 422 を返す。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: ABC を使う場合は `XxxInterface` 命名規則に準拠（CLAUDE.md §2 命名規則）。`@final` との組み合わせも既存ポリシーに矛盾しない。

**初心者でも安全な API 達成度**: `Literal` 型によるエンドポイント入力の制約が徹底されており、`class_name` や `formatter` への注入ベクターは完全に遮断されている。

**改善提案**: F-2 で発見した `Infinity`/`NaN` DoS 問題は FT212 と同一。nene2 フレームワークの `ErrorHandlerMiddleware` を修正して `RequestValidationError` の安全なシリアライズを組み込むことで、各 FT での重複回避策を不要にできる（Issue #594）。FT ごとに同じパターンを繰り返すのは設計の課題。
