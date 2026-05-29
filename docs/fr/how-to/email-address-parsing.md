# Guide pratique : analyser des adresses email et le comportement de parseaddr()

## parseaddr() est un analyseur permissif

`email.utils.parseaddr()` analyse les formats RFC 2822 (`"Name <addr@example.com>"`),
mais **il ne lève pas d'erreur sur une adresse malformée — il retourne une chaîne vide**.

```python
from email.utils import parseaddr

# Cas valides
parseaddr("Alice <alice@example.com>")  # → ("Alice", "alice@example.com")
parseaddr("alice@example.com")          # → ("", "alice@example.com")

# Adresses malformées — pas d'erreur, retourne ("", "")
parseaddr("not-an-email")               # → ("", "")
parseaddr("")                           # → ("", "")
parseaddr("bad @ format")              # → ("", "")
```

## Valider séparément à la frontière HTTP

Vérifier si la valeur de retour de `parseaddr()` est vide **ne suffit pas comme vérification
de sécurité**. Validez les adresses fournies par l'utilisateur avec `EmailStr` de Pydantic ou
une expression régulière *avant* d'utiliser `parseaddr()`.

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

## Se protéger contre l'injection d'en-têtes

Si un `Subject` ou un en-tête `From` contient CR/LF (`\r\n`), une **injection d'en-tête email**
peut se produire. `email.message.EmailMessage` l'échappe automatiquement, mais si vous passez
une chaîne brute à `smtplib.sendmail()`, supprimez CR/LF au préalable.

```python
import re
_INJECT_RE = re.compile(r"[\r\n]")

def sanitize_header(value: str) -> str:
    return _INJECT_RE.sub("", value)
```

## Issue liée

- [FT182] #511 : documenter le comportement permissif de `parseaddr()` dans un guide how-to
