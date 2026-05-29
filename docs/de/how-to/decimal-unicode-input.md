# How-to: Das decimal-Modul und Unicode-Zifferneingabe

## Pythons Decimal akzeptiert Unicode-Fullwidth-Ziffern

`decimal.Decimal()` interpretiert Unicode-Fullwidth-Ziffern (U+FF10–U+FF19:
０１２３４５６７８９) als Zahlen direkt. Wenn ein Benutzer Fullwidth-Ziffern über
eine HTTP-API einsendet, können sie **direkt durch ein Pydantic-`str`-Feld durchkommen**.

```python
from decimal import Decimal

Decimal("１２３")   # → Decimal('123')  ← normal umgewandelt
Decimal("１.５")   # → Decimal('1.5')
```

## Problem: Unerwartete Eingaben können durchkommen

In einer Finanzberechnungs-API, die `price: str = Field(...)` deklariert, wird bei einem Client-Eingang von `"１０００"` dies als `Decimal("１０００")` → `Decimal('1000')` verarbeitet. Das ist an sich kein Fehler, aber **wenn Sie normalisierte Eingabe benötigen** (Logging, DB-Speicherung, usw.), führen Sie Unicode-Normalisierung vor der Verarbeitung durch.

```python
import unicodedata
from decimal import Decimal

def parse_decimal_safe(value: str) -> Decimal:
    """Normalisieren (NFKC) und dann zu Decimal umwandeln."""
    normalized = unicodedata.normalize("NFKC", value.strip())
    return Decimal(normalized)
```

`unicodedata.normalize("NFKC", ...)` wandelt Fullwidth-Ziffern in Halbbreite um.

```python
unicodedata.normalize("NFKC", "１２３")  # → "123"
unicodedata.normalize("NFKC", "１.５")  # → "1.5"
```

## Validierung mit Pydantic

Wir empfehlen, Eingabe-Normalisierung mit einem Pydantic-`model_validator` zu erzwingen.

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

## Verwandtes Issue

- [FT176] #500: Das Verhalten der Fullwidth-Unicode-Zifferakzeptanz von `parse_decimal_safe()` dokumentieren
