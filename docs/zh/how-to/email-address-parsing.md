# 操作指南：解析邮件地址与 parseaddr() 的行为

## parseaddr() 是宽松解析器

`email.utils.parseaddr()` 解析 RFC 2822 格式（`"Name <addr@example.com>"`），但**对于格式错误的地址不会抛出异常 — 它返回空字符串**。

```python
from email.utils import parseaddr

# 有效情况
parseaddr("Alice <alice@example.com>")  # → ("Alice", "alice@example.com")
parseaddr("alice@example.com")          # → ("", "alice@example.com")

# 格式错误的地址 — 不报错，返回 ("", "")
parseaddr("not-an-email")               # → ("", "")
parseaddr("")                           # → ("", "")
parseaddr("bad @ format")              # → ("", "")
```

## 在 HTTP 边界单独验证

检查 `parseaddr()` 的返回值是否为空**不足以作为安全校验**。在使用 `parseaddr()` 之前，请先用 Pydantic 的 `EmailStr` 或正则表达式验证用户提供的地址。

```python
import re
from email.utils import parseaddr

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

def validate_and_parse(raw: str) -> tuple[str, str] | None:
    name, addr = parseaddr(raw)
    if not addr or not _EMAIL_RE.match(addr):
        return None
    return name, addr
```

## 防范邮件头注入

如果 `Subject` 或 `From` 头部包含 CR/LF（`\r\n`），可能发生**邮件头注入**。`email.message.EmailMessage` 会自动转义，但如果您将原始字符串传给 `smtplib.sendmail()`，请提前去除 CR/LF。

```python
import re
_INJECT_RE = re.compile(r"[\r\n]")

def sanitize_header(value: str) -> str:
    return _INJECT_RE.sub("", value)
```

## 相关 Issue

- [FT182] #511：在操作指南中记录 parseaddr() 的宽松行为
