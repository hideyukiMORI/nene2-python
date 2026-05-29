# Como fazer: parsing de endereços de email e o comportamento de parseaddr()

## parseaddr() é um parser permissivo

`email.utils.parseaddr()` faz parse de formatos RFC 2822 (`"Name <addr@example.com>"`),
mas **não lança exceção em endereços malformados — retorna uma string vazia**.

```python
from email.utils import parseaddr

# Casos válidos
parseaddr("Alice <alice@example.com>")  # → ("Alice", "alice@example.com")
parseaddr("alice@example.com")          # → ("", "alice@example.com")

# Endereços malformados — sem erro, retorna ("", "")
parseaddr("not-an-email")               # → ("", "")
parseaddr("")                           # → ("", "")
parseaddr("bad @ format")              # → ("", "")
```

## Valide na fronteira HTTP separadamente

Verificar se o valor retornado por `parseaddr()` está vazio **não é suficiente como
verificação de segurança**. Valide endereços fornecidos pelo usuário com o `EmailStr` do
Pydantic ou uma expressão regular *antes* de usar `parseaddr()`.

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

## Proteção contra injeção de header

Se um header `Subject` ou `From` contiver CR/LF (`\r\n`), pode ocorrer **injeção de
header de email**. `email.message.EmailMessage` escapa isso automaticamente, mas se você
passar uma string bruta para `smtplib.sendmail()`, remova CR/LF antes.

```python
import re
_INJECT_RE = re.compile(r"[\r\n]")

def sanitize_header(value: str) -> str:
    return _INJECT_RE.sub("", value)
```

## Issue relacionada

- [FT182] #511: documentar o comportamento permissivo de parseaddr() em um guia how-to
