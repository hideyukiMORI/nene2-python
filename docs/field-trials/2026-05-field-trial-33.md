# Field Trial 33: ValidationException カスタムエラーコード実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.3 時点
**テーマ**: `ValidationException` と `ValidationError.code` フィールドを活用した型安全なエラーコードの実運用パターン検証

---

## 概要

ユーザー登録 API を題材に、`ValidationCode(StrEnum)` パターンでドメイン固有のバリデーションコードを定義し、
`ValidationException` / `ValidationError` と組み合わせて複数フィールドの検証エラーをクライアントに返すフローを検証した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft33-validation-codes/` に以下を作成:

- **`app.py`** — `ValidationCode(StrEnum)` + `ValidationException` によるユーザー登録 API
- **`test_app.py`** — 正常系・各バリデーションエラー・複数エラー収集の動作テスト (5 件)
- **`test_friction.py`** — 摩擦点の確認テスト (3 件)

```python
class ValidationCode(StrEnum):
    REQUIRED = "required"
    INVALID_FORMAT = "invalid_format"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    ALREADY_EXISTS = "already_exists"
    OUT_OF_RANGE = "out_of_range"

def _validate_registration(body: RegisterBody) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if len(body.username) < 3:
        errors.append(ValidationError("username", "3文字以上必要です", ValidationCode.TOO_SHORT))
    if "@" not in body.email:
        errors.append(ValidationError("email", "有効なメールアドレスを入力してください", ValidationCode.INVALID_FORMAT))
    if body.age < 0 or body.age > 150:
        errors.append(ValidationError("age", "年齢は 0〜150 の範囲で入力してください", ValidationCode.OUT_OF_RANGE))
    return errors
```

**テスト結果**: 8 件全通過 ✅

---

## 摩擦点

### FP33-1: フレームワークが標準エラーコードを定義していない

**分類**: 設計通り（摩擦なし）

`required` / `invalid_format` / `too_short` / `too_long` 等のよく使うコードを
フレームワーク側が `ValidationCode` として提供していない。
各プロジェクトで自前定義が必要。

**判断**: ドメイン固有のコードはプロジェクトで定義するのが適切。フレームワークが網羅的に
定義すると過剰な依存・名前衝突・拡張困難になる。`StrEnum` パターンを how-to ドキュメントに
追記することで、新規プロジェクトの立ち上がりをサポートする。

**対応**: `docs/how-to/validation.md` への `StrEnum` パターン記載（ドキュメントのみ）

---

### FP33-2: `ValidationException.single()` の `code` パラメータにデフォルト値がない

**分類**: 既知の設計制約（摩擦なし）

`code` パラメータは必須。`"required"` 等よく使うコードでもデフォルト値なし。

**判断**: 明示的なコードが可読性・型安全性を高める設計上の意図。
デフォルト値をつけると「コードなし」での利用が増え、クライアント側でのエラーハンドリングが困難になる。
これは摩擦ではなく既知の制約として受け入れる。

---

### FP33-3: ネストフィールドのエラーパスに点記法ヘルパーがない

**分類**: 軽微な摩擦

`body.email` のようなネストパスを `ValidationError.field` に渡す際、正規化ヘルパーがない。
任意文字列として渡すのみ。

```python
error = ValidationError(field="address.city", message="必須です", code="required")
# 正規化なし — 任意の文字列を受け入れる
```

**判断**: ネストパスの表現方法（ドット区切り・スラッシュ・配列表記）はプロジェクトにより異なるため、
フレームワーク側でヘルパーを提供するメリットは小さい。
ドキュメントでの推奨パターン（ドット区切り）記載で対応。

---

## 所感

`ValidationCode(StrEnum)` パターンは極めて自然に機能する。
`ValidationError` コンストラクタに `StrEnum` 値をそのまま渡せるため、型安全性と
JSON シリアライズ（文字列として出力）が同時に確保される。複数フィールドのエラー収集も
リストに積み上げるだけで直感的。

フレームワーク側で追加の変更は不要。how-to ドキュメントへの `StrEnum` パターン追記のみ対応する。

---

## 関連

- `nene2.validation.ValidationException`
- `nene2.validation.ValidationError`
- FT13 (ValidationException実運用, v1.6.0) の後継検証
