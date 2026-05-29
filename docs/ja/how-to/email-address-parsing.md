# How-to: メールアドレスのパースと parseaddr() の挙動

## parseaddr() は寛容なパーサー

`email.utils.parseaddr()` は RFC 2822 準拠のフォーマット（`"Name <addr@example.com>"` 形式）を解析しますが、
**不正なアドレスを渡してもエラーを送出せず、空文字列を返します**。

```python
from email.utils import parseaddr

# 正常ケース
parseaddr("Alice <alice@example.com>")  # → ("Alice", "alice@example.com")
parseaddr("alice@example.com")          # → ("", "alice@example.com")

# 不正なアドレス — エラーにならず ("", "") を返す
parseaddr("not-an-email")               # → ("", "")
parseaddr("")                           # → ("", "")
parseaddr("bad @ format")              # → ("", "")
```

## HTTP 境界での検証は別途行うこと

`parseaddr()` の戻り値が空かどうかで有効性を確認しても、
**セキュリティ上の検証としては不十分**です。ユーザーが入力したアドレスは
Pydantic の `EmailStr` や正規表現で検証した後に `parseaddr()` を使ってください。

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

## ヘッダーインジェクション対策

`Subject` や `From` ヘッダーに CR/LF (`\r\n`) が含まれると
**メールヘッダーインジェクション**が発生します。`email.message.EmailMessage` を使えば
自動的にエスケープされますが、`smtplib.sendmail()` に生文字列を渡す場合は
事前に CR/LF を除去してください。

```python
import re
_INJECT_RE = re.compile(r"[\r\n]")

def sanitize_header(value: str) -> str:
    return _INJECT_RE.sub("", value)
```

## 関連 Issue

- [FT182] #511: parseaddr() の寛容な挙動を How-to ドキュメントに記載
