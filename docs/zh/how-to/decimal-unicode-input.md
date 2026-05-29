# 操作指南：decimal 模块与 Unicode 全角数字输入

## Python 的 Decimal 接受 Unicode 全角数字

`decimal.Decimal()` 会将 Unicode 全角数字（U+FF10–U+FF19：０１２３４５６７８９）直接识别为数字。当用户通过 HTTP API 提交全角数字时，它们可以**直接通过 Pydantic 的 `str` 字段**而不报错。

```python
from decimal import Decimal

Decimal("１２３")   # → Decimal('123')  ← 正常转换
Decimal("１.５")   # → Decimal('1.5')
```

## 问题：意外输入可能悄然通过

在一个声明了 `price: str = Field(...)` 的金融计算 API 中，如果客户端发送 `"１０００"`，会被当作 `Decimal("１０００")` → `Decimal('1000')` 处理。这本身不是错误，但**当您需要规范化输入时**（日志记录、数据库存储等），请在处理前进行 Unicode 规范化。

```python
import unicodedata
from decimal import Decimal

def parse_decimal_safe(value: str) -> Decimal:
    """规范化（NFKC）后转换为 Decimal。"""
    normalized = unicodedata.normalize("NFKC", value.strip())
    return Decimal(normalized)
```

`unicodedata.normalize("NFKC", ...)` 将全角数字转换为半角。

```python
unicodedata.normalize("NFKC", "１２３")  # → "123"
unicodedata.normalize("NFKC", "１.５")  # → "1.5"
```

## 使用 Pydantic 进行验证

建议使用 Pydantic 的 `model_validator` 强制进行输入规范化。

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

## 相关 Issue

- [FT176] #500：为 `parse_decimal_safe()` 的全角 Unicode 数字接受行为添加文档
