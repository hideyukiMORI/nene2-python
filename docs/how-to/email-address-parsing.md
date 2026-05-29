# How-to: parsing email addresses and the behavior of parseaddr()

## parseaddr() is a lenient parser

`email.utils.parseaddr()` parses RFC 2822 formats (`"Name <addr@example.com>"`),
but **it does not raise on a malformed address — it returns an empty string**.

```python
from email.utils import parseaddr

# Valid cases
parseaddr("Alice <alice@example.com>")  # → ("Alice", "alice@example.com")
parseaddr("alice@example.com")          # → ("", "alice@example.com")

# Malformed addresses — no error, returns ("", "")
parseaddr("not-an-email")               # → ("", "")
parseaddr("")                           # → ("", "")
parseaddr("bad @ format")              # → ("", "")
```

## Validate at the HTTP boundary separately

Checking whether `parseaddr()`'s return value is empty is **not sufficient as a
security check**. Validate user-supplied addresses with Pydantic's `EmailStr` or a
regular expression *before* using `parseaddr()`.

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

## Guarding against header injection

If a `Subject` or `From` header contains CR/LF (`\r\n`), **email header
injection** can occur. `email.message.EmailMessage` escapes this automatically,
but if you pass a raw string to `smtplib.sendmail()`, strip CR/LF beforehand.

```python
import re
_INJECT_RE = re.compile(r"[\r\n]")

def sanitize_header(value: str) -> str:
    return _INJECT_RE.sub("", value)
```

## Related issue

- [FT182] #511: document parseaddr()'s lenient behavior in a how-to guide
