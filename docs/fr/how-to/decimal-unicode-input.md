# Guide pratique : le module decimal et les entrées Unicode

## Python's Decimal accepte les chiffres Unicode pleine largeur

`decimal.Decimal()` interprète les chiffres Unicode pleine largeur (U+FF10–U+FF19 :
０１２３４５６７８９) comme des nombres directement. Quand un utilisateur soumet des chiffres
pleine largeur via une API HTTP, ils peuvent **passer directement à travers un champ Pydantic `str`**.

```python
from decimal import Decimal

Decimal("１２３")   # → Decimal('123')  ← converti normalement
Decimal("１.５")   # → Decimal('1.5')
```

## Problème : une entrée inattendue peut passer au travers

Dans une API de calcul financier qui déclare `price: str = Field(...)`, si un client envoie
`"１０００"`, il est traité comme `Decimal("１０００")` → `Decimal('1000')`. Ce n'est pas une
erreur en soi, mais **quand vous avez besoin d'entrées normalisées** (journalisation, stockage DB,
etc.), effectuez une normalisation Unicode avant le traitement.

```python
import unicodedata
from decimal import Decimal

def parse_decimal_safe(value: str) -> Decimal:
    """Normaliser (NFKC) puis convertir en Decimal."""
    normalized = unicodedata.normalize("NFKC", value.strip())
    return Decimal(normalized)
```

`unicodedata.normalize("NFKC", ...)` convertit les chiffres pleine largeur en demi-largeur.

```python
unicodedata.normalize("NFKC", "１２３")  # → "123"
unicodedata.normalize("NFKC", "１.５")  # → "1.5"
```

## Validation avec Pydantic

Nous recommandons de forcer la normalisation des entrées avec un `model_validator` Pydantic.

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

## Issue liée

- [FT176] #500 : documenter le comportement d'acceptation des chiffres Unicode pleine largeur de `parse_decimal_safe()`
