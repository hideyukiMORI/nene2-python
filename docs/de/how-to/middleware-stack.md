# How-to: Den Middleware-Stack korrekt konfigurieren

## Empfohlen: `setup_middlewares()` verwenden

Anstatt `add_middleware`-Aufrufe von Hand aufzureihen, verwenden Sie den vom Framework bereitgestellten Helfer, um LIFO-Reihenfolge-Fehler zu vermeiden (z. B. ein 500-Fehler ohne `X-Request-Id`).

```python
from nene2.middleware import setup_middlewares

setup_middlewares(
    app,
    debug=cfg.app_debug,
    domain_handlers=[NoteNotFoundExceptionHandler()],
    throttle_limit=cfg.throttle_limit if cfg.throttle_enabled else None,
    max_request_bytes=cfg.max_body_size,
    cors_allowed_origins=cfg.cors_origins if cfg.cors_enabled else None,
)
```

Resultierender Stack (von außen nach innen):

```
CORS → RequestId → SecurityHeaders → SizeLimit → Throttle → RequestLogging → ErrorHandler
```

Verwenden Sie das manuelle Registrierungsmuster unten nur, wenn Sie benutzerdefinierte Middleware benötigen.

---

## Manuelle Registrierung (TL;DR)

```python
# add_middleware in dieser Reihenfolge aufrufen
app.add_middleware(ErrorHandlerMiddleware)           # innerste
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ThrottleMiddleware, limit=100, window=60)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)              # äußerste
```

---

## Warum diese Reihenfolge

### Starletttes LIFO-Regel

`app.add_middleware()` macht **die zuletzt hinzugefügte zur äußersten** (LIFO).

```
add_middleware(A)  →  B(A(Router))
add_middleware(B)
```

Die Anfrage fließt von außen nach innen (B → A → Router), und die Antwort von innen nach außen (Router → A → B).

### Was bricht, wenn ErrorHandler äußerste ist

```python
# ❌ falsch
app.add_middleware(RequestIdMiddleware)
app.add_middleware(ErrorHandlerMiddleware)  # äußerste
# Stack: ErrorHandler(RequestId(Router))
```

Wenn ein Handler eine Ausnahme auslöst:

1. `ErrorHandlerMiddleware.dispatch` fängt die Ausnahme ab
2. es gibt eine **brandneue Response direkt** über `problem_details_response(...)` zurück
3. diese Response **durchläuft nicht** die innere `RequestId`-Middleware
4. Ergebnis: **der 500-Fehler hat kein `X-Request-Id`**

Aus demselben Grund erhalten Fehlerantworten keine Sicherheitsheader, wenn `SecurityHeadersMiddleware` innen ist.

### Das korrekte Stack-Diagramm

```
RequestIdMiddleware            ← fügt jeder Antwort X-Request-Id hinzu (200–5xx)
  └─ SecurityHeadersMiddleware ← fügt jeder Antwort Sicherheitsheader hinzu
       └─ RequestSizeLimitMiddleware ← gibt 413 direkt zurück (kein ErrorHandler nötig)
            └─ ThrottleMiddleware   ← gibt 429 direkt zurück (kein ErrorHandler nötig)
                 └─ RequestLoggingMiddleware
                      └─ ErrorHandlerMiddleware ← wandelt Handler-Ausnahmen in 500 um
                           └─ Router (FastAPI-Handler)
```

`RequestSizeLimitMiddleware` und `ThrottleMiddleware` geben `problem_details_response()` selbst zurück, daher ändert die Platzierung innerhalb oder außerhalb des ErrorHandlers nicht das 413/429-Format. Ob `X-Request-Id` angehängt wird, hängt von der Position von `RequestIdMiddleware` ab.

---

## Wenn einige Middlewares nicht verwendet werden

Auch wenn Sie einige Middlewares weglassen, gilt dieselbe Reihenfolgeregel:

```python
# wenn ThrottleMiddleware und RequestLoggingMiddleware weggelassen werden
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
```

---

## Bei Verwendung von ErrorHandlerMiddleware.install()

`install()` führt `add_middleware` und `add_exception_handler` zusammen aus, aber Sie müssen die Reihenfolge relativ zu anderen Middlewares dennoch manuell festlegen:

```python
# install() zuerst aufrufen (wird innerste)
ErrorHandlerMiddleware.install(app)          # innen

# dann die anderen Middlewares hinzufügen
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)       # außen
```

---

## FAQ

**F: Soll `RequestSizeLimitMiddleware` innerhalb oder außerhalb des ErrorHandlers sein?**

A: Beides funktioniert, aber wenn sie innerhalb von `RequestIdMiddleware` platziert wird, erhält die 413-Antwort auch eine `X-Request-Id`. Befolgen Sie einfach die empfohlene Reihenfolge oben.

**F: Wo füge ich benutzerdefinierte Middleware hinzu?**

A: Das hängt von der Art der Middleware ab:
- Etwas zu jeder Antwort hinzufügen → direkt vor `RequestIdMiddleware` (außen)
- Handler-Ausnahmen abfangen → direkt nach `ErrorHandlerMiddleware` (innen)
- Anfragen früh ablehnen → in der Nähe von `RequestSizeLimitMiddleware` oder `ThrottleMiddleware`
