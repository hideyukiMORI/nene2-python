# FT212: dataclasses モジュール — field / asdict / astuple / replace / __post_init__

**日付**: 2026-05-22
**テーマ**: Python `dataclasses` モジュールの field / asdict / astuple / replace / __post_init__ の実装と検証
**セキュリティ診断**: なし（212 % 3 = 2）
**クラッカーペンテスト**: あり（212 % 4 = 0）

---

## 概要

`dataclasses` モジュールは Python 3.7 以降標準の構造化データクラス生成ユーティリティ。今 FT では静的解析だけでなく「実行時のデータ変換・不変条件の強制」パターンを重点的に検証した。

| API | ユースケース |
|---|---|
| `@dataclass(frozen=True, slots=True)` | immutable value object（メモリ効率・ハッシュ可能） |
| `field(default_factory=list/dict)` | ミュータブルデフォルトの安全な管理 |
| `asdict()` | dataclass → dict 変換（深いコピー） |
| `astuple()` | dataclass → tuple 変換 |
| `replace()` | フィールドを置換した新インスタンス生成（immutable 更新） |
| `__post_init__` | 初期化後の不変条件チェック |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft212-dataclasses/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `Vector3D` | `frozen=True, slots=True` + `__post_init__` で有限値・範囲チェック |
| `vector_to_dict` | `asdict(Vector3D(...))` で dict 変換・大きさ計算 |
| `vector_to_tuple` | `astuple(Vector3D(...))` で tuple 変換 |
| `translate_vector` | `replace(original, x=..., y=..., z=...)` で新インスタンスを生成 |
| `TaggedItem` | `field(default_factory=list/dict)` のミュータブルデフォルト管理 |
| `BoundedRange` | `__post_init__` で `low < high` の不変条件を強制 |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/dataclasses/vector-dict` | asdict 変換・大きさ計算 |
| POST | `/dataclasses/vector-tuple` | astuple 変換 |
| POST | `/dataclasses/vector-translate` | replace による並進移動 |
| POST | `/dataclasses/tagged-item` | field(default_factory) のデモ |
| POST | `/dataclasses/range` | __post_init__ で low < high を強制 |

---

## 摩擦点

### F-1: `astuple` の戻り値型は常に `tuple[object, ...]`

**観察**: `astuple(vector)` の戻り値型が `tuple[Any, ...]` となるため、型安全に `tuple[float, float, float]` として使いたい場合は別途キャストまたは型注釈が必要。

**対処**: `components = astuple(vector)` の後に `VectorTupleResult(components=components, ...)` で包んで型安全な返却を行うことで mypy エラーを回避。`astuple` は深いコピーの変換ユーティリティとして使い、型付きの結果は dataclass でラップするパターンが有効。

---

### F-2（HIGH）: `Infinity`/`NaN` 非標準 JSON がエラーシリアライザーを 500 クラッシュさせる

**発見**: クラッカーペンテストで発見。非標準 JSON ボディを直接バイト列で送信した場合:

```
POST /dataclasses/vector-dict
Content-Type: application/json
Body: {"x": Infinity, "y": 0.0, "z": 0.0}
```

**挙動連鎖**:
1. Python 3.14 の JSON パーサーが `Infinity` を `float('inf')` として受け入れる（JSON spec 違反だが Python が許容）
2. Pydantic の `ge=-1000000, le=1000000` バリデーションが `inf` に対して False → `RequestValidationError` を発生
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

**根本対策**: nene2 の `ErrorHandlerMiddleware` または `RequestValidationError` ハンドラーを標準化して非有限 float をサニタイズすべき（Issue #594 参照）。

---

## クラッカーペンテスト結果

| 攻撃シナリオ | 結果 | 対処 |
|---|---|---|
| `Infinity` を非標準 JSON で送信 | **修正済み (F-2)** → 422 | `_sanitize_value` + カスタムハンドラー |
| `NaN` を非標準 JSON で送信 | **修正済み (F-2)** → 422 | 同上 |
| `MAX_COORDINATE+1` の座標 | 422（Pydantic `le=` で遮断） | 対策済み |
| `MAX_COORDINATE` の座標 → 境界値 | 200（正常） | 問題なし |
| translate で合計が範囲超え | 422（`__post_init__` で遮断） | 対策済み |
| タグ 51 個（上限 50） | 422（Pydantic `max_length=50` で遮断） | 対策済み |
| タグ 200 個 | 422（同上） | 対策済み |
| タグ文字列 600 文字 | 422（`_BoundedStr max_length=500`） | 対策済み |
| range `NaN` 非標準 JSON | **修正済み (F-2)** → 422 | 同上 |
| 空文字列の name | 422（`min_length=1`） | 対策済み |

**総合評価: 堅牢**（F-2 修正後）

---

## テスト結果

```
25 passed in 0.44s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`@dataclass` は「属性と `__init__` を自動生成してくれる魔法」として理解できる。`frozen=True` が「変更できないクラス」という概念は分かりやすい。`field(default_factory=list)` の必要性（`tags: list = []` が危険な理由）は初見では気づきにくいが、`TaggedItem` のデモを見れば「なぜ必要か」が伝わる。

**ドキュメント理解**: `asdict` と `astuple` の違い（dict = 名前付き / tuple = 順序依存）は具体例があれば分かりやすい。

**事故リスク（中）**: `field(default_factory=list)` を知らないと `tags: list = []` を書いて全インスタンスがリストを共有するバグが起きる。nene2 の `dataclass(frozen=True, slots=True)` 強制はこのリスクを大幅に削減する（frozen だとリスト型フィールドを持てないので必然的に `field(default_factory)` を使う）。

**規約の使いやすさ**: `__post_init__` バリデーションは「コンストラクタ後に実行される」という説明があれば直感的。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`asdict` で dict に変換して JSON に渡すパターンはよく使う。`replace` による immutable 更新は TypeScript の spread (`{...obj, x: 10}`) と類似概念で理解しやすい。`__post_init__` は Django の `clean()` に相当する。

**コピペ可能性**: `Vector3D + translate_vector` のパターンはほぼそのまま2Dゲームや座標計算に流用できる。

**拡張時の罠**: `astuple` はネストしたデータクラスも再帰的にタプル化する。`asdict` も同様。これを知らないと予期しない構造が返ってくる可能性がある。

**事故リスク（低）**: `__post_init__` でバリデーションしているため、無効な状態のオブジェクトが生成されない。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `readonly interface` と `Object.freeze()` に相当する。`replace()` は TypeScript の `{...original, x: newX}` スプレッドと同じ意図。`field(default_factory)` は TypeScript では不要（参照型をクラスに持たせるとき React の state 更新パターンと類似する）。

**エラーレスポンスの質**: 422 の詳細が`{field, message, code}` 形式で一貫しており TS のバリデーションエラーと同様に扱える。

**Python 固有概念**: `__post_init__` はコンストラクタと別ファイルで定義できないが、TS のクラスコンストラクタよりシンプル。

**事故リスク（低）**: F-2 修正後は 422 を返すため、フロントエンドが適切にエラーを処理できる。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`asdict` + `replace` パターンは Django の `model_to_dict` + `Model(instance=obj)` より軽量。`frozen=True, slots=True` の組み合わせは Python のベストプラクティスとして定着しており評価できる。

**他フレームワークとの差異**: Django ORM の `Model` はミュータブルだが、nene2 の domain 層は全て `frozen=True` で設計されており、値の変更は `replace()` を通じてのみ行う。これにより副作用が生じにくい。

**nene2 の薄さへの評価**: F-2 の修正が app.py の `create_app()` にカスタムハンドラーを追加する形になっているのは理想的ではない（フレームワーク側で解決すべき）。Issue として追跡していることは評価できる。

**事故リスク（低）**: 境界値チェックが Pydantic と `__post_init__` で二重に保護されており堅牢。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `dataclass` でリスト/dict フィールドを使う場合、`field(default_factory=...)` を使っているか
- `frozen=True` の dataclass では `__post_init__` のバリデーションに `object.__setattr__` が不要（`frozen=True` でも `__post_init__` で値を読むことはできる）
- `asdict` の戻り値が `dict[str, Any]` になる点と `astuple` の型消失を理解した上で使っているか

**チームでの安全なパターン**: `__post_init__` でバリデーションして `ValueError` を上げ、HTTP 層で `ValidationException` に変換するパターンは明確で良い。

**事故リスク（低）**: F-2 修正後は全攻撃シナリオで 422 を返す。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `frozen=True, slots=True` を標準とするポリシーが今 FT でも一貫して適用されている。`field(default_factory)` パターンは Python の `dataclasses` ベストプラクティスとして CLAUDE.md に追記する価値がある。

**初心者でも安全な API 達成度**: `_Coord = Annotated[float, Field(ge=..., le=...)]` でバウンダリを型エイリアスにまとめ、全エンドポイントで一貫した境界チェックを実現。

**改善提案**: F-2 で発見した `Infinity`/`NaN` DoS 問題を nene2 フレームワークレベルで修正する（`ErrorHandlerMiddleware` に `RequestValidationError` の安全なシリアライズを統合）。これは全 FT に共通する問題であり、今後の FT でも再発する可能性がある。
