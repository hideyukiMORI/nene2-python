# How-to: configuring the middleware stack correctly

## Recommended: use `setup_middlewares()`

Instead of lining up `add_middleware` calls by hand, use the framework-provided
helper to avoid LIFO ordering mistakes (such as a 500 not getting an
`X-Request-Id`).

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

Resulting stack (outer → inner):

```
CORS → RequestId → SecurityHeaders → SizeLimit → Throttle → RequestLogging → ErrorHandler
```

Use the manual registration pattern below only when you need custom middleware.

---

## Manual registration (TL;DR)

```python
# call add_middleware in this order
app.add_middleware(ErrorHandlerMiddleware)           # innermost
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ThrottleMiddleware, limit=100, window=60)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)              # outermost
```

---

## Why this order

### Starlette's LIFO rule

`app.add_middleware()` makes **the last one added the outermost** (LIFO).

```
add_middleware(A)  →  B(A(Router))
add_middleware(B)
```

The request flows outer → inner (B → A → Router), and the response flows
inner → outer (Router → A → B).

### What breaks if ErrorHandler is outermost

```python
# ❌ wrong
app.add_middleware(RequestIdMiddleware)
app.add_middleware(ErrorHandlerMiddleware)  # outermost
# stack: ErrorHandler(RequestId(Router))
```

When a handler raises an exception:

1. `ErrorHandlerMiddleware.dispatch` catches the exception
2. it returns a **brand new Response directly** via `problem_details_response(...)`
3. that Response **does not pass through** the inner `RequestId` middleware
4. result: **the 500 error has no `X-Request-Id`**

For the same reason, if `SecurityHeadersMiddleware` is inner, error responses
won't get security headers.

### The correct stack diagram

```
RequestIdMiddleware            ← adds X-Request-Id to every response (200–5xx)
  └─ SecurityHeadersMiddleware ← adds security headers to every response
       └─ RequestSizeLimitMiddleware ← returns 413 directly (no ErrorHandler needed)
            └─ ThrottleMiddleware   ← returns 429 directly (no ErrorHandler needed)
                 └─ RequestLoggingMiddleware
                      └─ ErrorHandlerMiddleware ← converts handler exceptions to 500
                           └─ Router (FastAPI handlers)
```

`RequestSizeLimitMiddleware` and `ThrottleMiddleware` return
`problem_details_response()` themselves, so placing them inside or outside the
ErrorHandler doesn't change the 413/429 format. Whether `X-Request-Id` is attached
depends on the position of `RequestIdMiddleware`.

---

## When some middleware is unused

Even if you omit some middleware, the rest follows the same ordering rule:

```python
# when ThrottleMiddleware and RequestLoggingMiddleware are omitted
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
```

---

## When using ErrorHandlerMiddleware.install()

`install()` does `add_middleware` and `add_exception_handler` together, but you
still need to set the order relative to other middleware manually:

```python
# call install() first (it becomes innermost)
ErrorHandlerMiddleware.install(app)          # inner

# then add the other middleware
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)       # outer
```

---

## FAQ

**Q: Should `RequestSizeLimitMiddleware` go inside or outside the ErrorHandler?**

A: It works either way, but placing it inside `RequestIdMiddleware` means the 413
response also gets an `X-Request-Id`. Just follow the recommended order above.

**Q: Where do I add custom middleware?**

A: It depends on the middleware's nature:
- want to add something to every response → right before `RequestIdMiddleware` (outer)
- want to catch handler exceptions → right after `ErrorHandlerMiddleware` (inner)
- want to reject requests early → near `RequestSizeLimitMiddleware` or `ThrottleMiddleware`
