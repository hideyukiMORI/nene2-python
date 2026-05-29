# How-to: E-Mail-Adressen parsen und das Verhalten von parseaddr()

## parseaddr() ist ein nachsichtiger Parser

`email.utils.parseaddr()` parst RFC-2822-Formate (`"Name <addr@example.com>"`),
aber **es löst bei einer fehlerhaften Adresse keine Ausnahme aus — es gibt einen leeren String zurück**.

```python
from email.utils import parseaddr

# Gültige Fälle
parseaddr("Alice <alice@example.com>")  # → ("Alice", "alice@example.com")
parseaddr("alice@example.com")          # → ("", "alice@example.com")

# Fehlerhafte Adressen — kein Fehler, gibt ("", "") zurück
parseaddr("not-an-email")               # → ("", "")
parseaddr("")                           # → ("", "")
parseaddr("bad @ format")              # → ("", "")
```

## An der HTTP-Grenze separat validieren

Das Prüfen, ob der Rückgabewert von `parseaddr()` leer ist, **reicht nicht als Sicherheitsprüfung aus**. Validieren Sie von Benutzern angegebene Adressen mit Pydantics `EmailStr` oder einem regulären Ausdruck *bevor* Sie `parseaddr()` verwenden.

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

## Schutz vor Header-Injection

Wenn ein `Subject`- oder `From`-Header CR/LF (`\r\n`) enthält, kann **E-Mail-Header-Injection** auftreten. `email.message.EmailMessage` maskiert dies automatisch, aber wenn Sie einen rohen String an `smtplib.sendmail()` übergeben, entfernen Sie CR/LF vorher.

```python
import re
_INJECT_RE = re.compile(r"[\r\n]")

def sanitize_header(value: str) -> str:
    return _INJECT_RE.sub("", value)
```

## Verwandtes Issue

- [FT182] #511: Das nachsichtige Verhalten von parseaddr() in einem How-to-Leitfaden dokumentieren
