# Guide pratique : configurer correctement la pile middleware

## Recommandé : utiliser `setup_middlewares()`

Plutôt que d'aligner des appels `add_middleware` à la main, utilisez le helper fourni par le
framework pour éviter les erreurs d'ordre LIFO (comme un 500 sans `X-Request-Id`).

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

Pile résultante (externe → interne) :

```
CORS → RequestId → SecurityHeaders → SizeLimit → Throttle → RequestLogging → ErrorHandler
```

N'utilisez le schéma d'enregistrement manuel ci-dessous que si vous avez besoin d'un middleware
personnalisé.

---

## Enregistrement manuel (en bref)

```python
# appeler add_middleware dans cet ordre
app.add_middleware(ErrorHandlerMiddleware)           # le plus interne
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ThrottleMiddleware, limit=100, window=60)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)              # le plus externe
```

---

## Pourquoi cet ordre

### La règle LIFO de Starlette

`app.add_middleware()` fait en sorte que **le dernier ajouté est le plus externe** (LIFO).

```
add_middleware(A)  →  B(A(Router))
add_middleware(B)
```

La requête circule de l'externe vers l'interne (B → A → Router), et la réponse de l'interne
vers l'externe (Router → A → B).

### Ce qui se casse si ErrorHandler est le plus externe

```python
# ❌ incorrect
app.add_middleware(RequestIdMiddleware)
app.add_middleware(ErrorHandlerMiddleware)  # le plus externe
# pile : ErrorHandler(RequestId(Router))
```

Quand un handler lève une exception :

1. `ErrorHandlerMiddleware.dispatch` capture l'exception
2. il retourne une **nouvelle Response directement** via `problem_details_response(...)`
3. cette Response **ne passe pas par** le middleware `RequestId` interne
4. résultat : **l'erreur 500 n'a pas de `X-Request-Id`**

Pour la même raison, si `SecurityHeadersMiddleware` est interne, les réponses d'erreur
n'auront pas les en-têtes de sécurité.

### Le diagramme de pile correct

```
RequestIdMiddleware            ← ajoute X-Request-Id à chaque réponse (200–5xx)
  └─ SecurityHeadersMiddleware ← ajoute les en-têtes de sécurité à chaque réponse
       └─ RequestSizeLimitMiddleware ← retourne 413 directement (pas besoin d'ErrorHandler)
            └─ ThrottleMiddleware   ← retourne 429 directement (pas besoin d'ErrorHandler)
                 └─ RequestLoggingMiddleware
                      └─ ErrorHandlerMiddleware ← convertit les exceptions de handler en 500
                           └─ Router (handlers FastAPI)
```

`RequestSizeLimitMiddleware` et `ThrottleMiddleware` retournent eux-mêmes
`problem_details_response()`, donc les placer à l'intérieur ou à l'extérieur de l'ErrorHandler
ne change pas le format 413/429. L'attachement de `X-Request-Id` dépend de la position de
`RequestIdMiddleware`.

---

## Quand certains middleware ne sont pas utilisés

Même si vous omettez certains middleware, les autres suivent la même règle d'ordre :

```python
# quand ThrottleMiddleware et RequestLoggingMiddleware sont omis
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
```

---

## Quand on utilise ErrorHandlerMiddleware.install()

`install()` fait `add_middleware` et `add_exception_handler` ensemble, mais vous devez quand
même définir l'ordre par rapport aux autres middleware manuellement :

```python
# appeler install() en premier (il devient le plus interne)
ErrorHandlerMiddleware.install(app)          # interne

# puis ajouter les autres middleware
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)       # externe
```

---

## FAQ

**Q : `RequestSizeLimitMiddleware` doit-il aller à l'intérieur ou à l'extérieur de l'ErrorHandler ?**

R : Les deux fonctionnent, mais le placer à l'intérieur de `RequestIdMiddleware` signifie que
la réponse 413 obtient également un `X-Request-Id`. Suivez simplement l'ordre recommandé ci-dessus.

**Q : Où ajouter un middleware personnalisé ?**

R : Cela dépend de la nature du middleware :
- vous voulez ajouter quelque chose à chaque réponse → juste avant `RequestIdMiddleware` (externe)
- vous voulez capturer les exceptions du handler → juste après `ErrorHandlerMiddleware` (interne)
- vous voulez rejeter les requêtes tôt → près de `RequestSizeLimitMiddleware` ou `ThrottleMiddleware`
