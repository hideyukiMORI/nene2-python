# How-to: the decimal module and Unicode digit input

## Python's Decimal accepts Unicode full-width digits

`decimal.Decimal()` interprets Unicode full-width digits (U+FF10–U+FF19:
０１２３４５６７８９) as numbers as-is. When a user submits full-width digits through
an HTTP API, they can **pass straight through a Pydantic `str` field**.

```python
from decimal import Decimal

Decimal("１２３")   # → Decimal('123')  ← converted normally
Decimal("１.５")   # → Decimal('1.5')
```

## Problem: unexpected input may slip through

In a financial-calculation API that declares `price: str = Field(...)`, if a
client sends `"１０００"` it is processed as `Decimal("１０００")` → `Decimal('1000')`.
That is not an error in itself, but **when you need normalized input** (logging,
DB storage, etc.) perform Unicode normalization before processing.

```python
import unicodedata
from decimal import Decimal

def parse_decimal_safe(value: str) -> Decimal:
    """Normalize (NFKC) then convert to Decimal."""
    normalized = unicodedata.normalize("NFKC", value.strip())
    return Decimal(normalized)
```

`unicodedata.normalize("NFKC", ...)` converts full-width digits to half-width.

```python
unicodedata.normalize("NFKC", "１２３")  # → "123"
unicodedata.normalize("NFKC", "１.５")  # → "1.5"
```

## Validation with Pydantic

We recommend forcing input normalization with a Pydantic `model_validator`.

```python
from pydantic import BaseModel, Field, model_validator

class PriceRequest(BaseModel):
    price: str = Field(max_length=20, description="Price (half-width digits)")

    @model_validator(mode="before")
    @classmethod
    def normalize_unicode(cls, values: dict) -> dict:
        import unicodedata
        if "price" in values and isinstance(values["price"], str):
            values["price"] = unicodedata.normalize("NFKC", values["price"])
        return values
```

## Related issue

- [FT176] #500: document the full-width Unicode digit acceptance behavior of `parse_decimal_safe()`
