# How-to: decimal モジュールと Unicode 数字入力

## Python の Decimal は Unicode 全角数字を受け入れる

`decimal.Decimal()` は Unicode の全角数字（U+FF10〜U+FF19: ０１２３４５６７８９）を
そのまま数値として解釈します。HTTP API を通じてユーザーが全角数字を入力した場合、
**Pydantic の `str` フィールドを通過してしまう**ことがあります。

```python
from decimal import Decimal

Decimal("１２３")   # → Decimal('123')  ← 正常に変換される
Decimal("１.５")   # → Decimal('1.5')
```

## 問題: 想定外の入力が通過する可能性

金融計算 API で `price: str = Field(...)` としている場合、
クライアントが `"１０００"` を送ると `Decimal("１０００")` → `Decimal('1000')` として処理されます。
これ自体はエラーではありませんが、**入力の正規化が必要な場合**（ログ記録・DB 保存等）は
Unicode 正規化を行ってから処理してください。

```python
import unicodedata
from decimal import Decimal

def parse_decimal_safe(value: str) -> Decimal:
    """Unicode 正規化（NFKC）して Decimal に変換する."""
    normalized = unicodedata.normalize("NFKC", value.strip())
    return Decimal(normalized)
```

`unicodedata.normalize("NFKC", ...)` は全角数字を半角に変換します。

```python
unicodedata.normalize("NFKC", "１２３")  # → "123"
unicodedata.normalize("NFKC", "１.５")  # → "1.5"
```

## Pydantic でのバリデーション

Pydantic の `model_validator` を使って入力値の正規化を強制することを推奨します。

```python
from pydantic import BaseModel, Field, model_validator

class PriceRequest(BaseModel):
    price: str = Field(max_length=20, description="価格（半角数字）")

    @model_validator(mode="before")
    @classmethod
    def normalize_unicode(cls, values: dict) -> dict:
        import unicodedata
        if "price" in values and isinstance(values["price"], str):
            values["price"] = unicodedata.normalize("NFKC", values["price"])
        return values
```

## 関連 Issue

- [FT176] #500: parse_decimal_safe() の Unicode 全角数字受け入れ挙動を文書化
