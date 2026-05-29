# Como fazer: o módulo decimal e entrada de dígitos Unicode

## Python's Decimal aceita dígitos Unicode de largura total

`decimal.Decimal()` interpreta dígitos Unicode de largura total (U+FF10–U+FF19:
０１２３４５６７８９) como números normalmente. Quando um usuário submete dígitos de largura total
por uma API HTTP, eles podem **passar direto por um campo Pydantic `str`**.

```python
from decimal import Decimal

Decimal("１２３")   # → Decimal('123')  ← convertido normalmente
Decimal("１.５")   # → Decimal('1.5')
```

## Problema: entrada inesperada pode passar despercebida

Em uma API de cálculo financeiro que declara `price: str = Field(...)`, se um
cliente enviar `"１０００"`, isso é processado como `Decimal("１０００")` → `Decimal('1000')`.
Isso não é um erro em si, mas **quando você precisa de entrada normalizada** (logging,
armazenamento em DB, etc.) realize a normalização Unicode antes de processar.

```python
import unicodedata
from decimal import Decimal

def parse_decimal_safe(value: str) -> Decimal:
    """Normaliza (NFKC) e então converte para Decimal."""
    normalized = unicodedata.normalize("NFKC", value.strip())
    return Decimal(normalized)
```

`unicodedata.normalize("NFKC", ...)` converte dígitos de largura total para meia largura.

```python
unicodedata.normalize("NFKC", "１２３")  # → "123"
unicodedata.normalize("NFKC", "１.５")  # → "1.5"
```

## Validação com Pydantic

Recomendamos forçar a normalização de entrada com um `model_validator` do Pydantic.

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

## Issue relacionada

- [FT176] #500: documentar o comportamento de aceitação de dígitos Unicode de largura total de `parse_decimal_safe()`
