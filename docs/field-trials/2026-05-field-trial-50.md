# Field Trial 50: ValidationException + ValidationCode(StrEnum) 実運用検証

**Date**: 2026-05-20
**Theme**: `ValidationException` + `ValidationCode(StrEnum)` の実運用パターン検証
**Version under test**: v1.8.9
**FT App**: `/home/xi/docker/nene2-python-FT/ft50-validation/`

---

## 概要

複数フィールドバリデーション (`ValidationException` + `ValidationError` リスト) と
`ValidationCode(StrEnum)` による型安全なエラーコードの組み合わせを、
商品作成 API で実運用した。

---

## 実装内容

### `ProductCode(StrEnum)` によるエラーコード定義

```python
class ProductCode(StrEnum):
    required = "required"
    out_of_range = "out_of_range"
    invalid_format = "invalid_format"
    duplicate = "duplicate"
```

`StrEnum` を継承することで、エラーコードが静的解析で型チェックされる。
レスポンスの `code` フィールドには文字列値（`"required"` 等）がそのまま出力される。

### 複数フィールドバリデーション

```python
def validate_product(name: str, price: int, sku: str, stock: int) -> None:
    errors: list[ValidationError] = []
    if not name.strip():
        errors.append(ValidationError("name", "Name is required.", ProductCode.required))
    if price < 0:
        errors.append(ValidationError("price", "Price must be non-negative.", ProductCode.out_of_range))
    # ...
    if errors:
        raise ValidationException(errors)
```

エラーを収集してから一括で `raise ValidationException(errors)` するパターン。

### 単一フィールド専用例外

```python
if body.sku in _existing_skus:
    raise ValidationException.single("sku", f"SKU '{body.sku}' already exists.", ProductCode.duplicate)
```

`ValidationException.single()` classmethod で 1 行で単一エラーを raise できる。

---

## テスト結果

12 tests, all passed.

| テスト | 結果 |
|---|---|
| 正常系: 商品作成成功 | ✅ |
| 単一フィールドエラー (price < 0) | ✅ |
| 複数フィールドエラー | ✅ |
| price 上限チェック (> 1,000,000) | ✅ |
| SKU フォーマット検証 | ✅ |
| 重複 SKU (ValidationException.single) | ✅ |
| ValidationCode 値が文字列として返る | ✅ |
| 422 Problem Details 構造確認 | ✅ |
| StrEnum 値がレスポンスで文字列になる | ✅ |
| message フィールドがレスポンスに含まれる | ✅ |
| 同一フィールド複数エラー | ✅ |
| エラーリストの順序が検証順と一致 | ✅ |

---

## 摩擦ポイント

摩擦なし。以下の点がすべて期待通りに動作した:

- **FP50-1 (確認済み)**: `ValidationCode(StrEnum)` の値はレスポンスの `code` フィールドに文字列として正しく出力される。`StrEnum` は `str` のサブクラスなので JSON シリアライズ時に文字列化される。
- **FP50-2 (確認済み)**: `ValidationError` の `message` フィールドがレスポンスの各エラーオブジェクトに含まれる。
- **FP50-3 (確認済み)**: 同一フィールドへの複数エラー収集は設計上サポートされており、正常に動作する。
- **FP50-4 (確認済み)**: `ValidationException(errors)` はエラーリストの順序を保持する。

---

## フレームワーク変更

なし。

---

## 結論

`ValidationException` + `ValidationCode(StrEnum)` の組み合わせは実運用で摩擦なく使える。
エラーコードを `StrEnum` で定義することで:

1. IDE/mypy による型補完・チェックが得られる
2. レスポンスには文字列値がそのまま出力される（追加設定不要）
3. `validate_product()` 関数でエラーを収集して一括 raise するパターンが自然に書ける
4. 単一フィールドの場合は `ValidationException.single()` で 1 行で済む

API クライアントは `code` 文字列でエラー種別を判定できる。
