# 操作指南：正确配置 middleware 栈

## 推荐：使用 `setup_middlewares()`

建议使用框架提供的帮助函数，而非手动逐行调用 `add_middleware`，可避免 LIFO 顺序错误（如 500 响应缺少 `X-Request-Id`）。

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

产生的栈（从外到内）：

```
CORS → RequestId → SecurityHeaders → SizeLimit → Throttle → RequestLogging → ErrorHandler
```

只有当需要自定义 middleware 时，才使用下面的手动注册模式。

---

## 手动注册（简要版）

```python
# 按此顺序调用 add_middleware
app.add_middleware(ErrorHandlerMiddleware)           # 最内层
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ThrottleMiddleware, limit=100, window=60)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)              # 最外层
```

---

## 为何这样排序

### Starlette 的 LIFO 规则

`app.add_middleware()` 使**最后添加的成为最外层**（LIFO）。

```
add_middleware(A)  →  B(A(Router))
add_middleware(B)
```

请求从外到内流动（B → A → Router），响应从内到外流动（Router → A → B）。

### ErrorHandler 在最外层时会出现什么问题

```python
# ❌ 错误
app.add_middleware(RequestIdMiddleware)
app.add_middleware(ErrorHandlerMiddleware)  # 最外层
# 栈：ErrorHandler(RequestId(Router))
```

当 handler 抛出异常时：

1. `ErrorHandlerMiddleware.dispatch` 捕获异常
2. 直接通过 `problem_details_response(...)` 返回一个**全新的 Response**
3. 该 Response **不经过**内层的 `RequestId` middleware
4. 结果：**500 错误没有 `X-Request-Id`**

同理，如果 `SecurityHeadersMiddleware` 在内层，错误响应也不会包含安全头。

### 正确的栈示意图

```
RequestIdMiddleware            ← 为每个响应（200–5xx）添加 X-Request-Id
  └─ SecurityHeadersMiddleware ← 为每个响应添加安全头
       └─ RequestSizeLimitMiddleware ← 直接返回 413（不需要 ErrorHandler）
            └─ ThrottleMiddleware   ← 直接返回 429（不需要 ErrorHandler）
                 └─ RequestLoggingMiddleware
                      └─ ErrorHandlerMiddleware ← 将 handler 异常转换为 500
                           └─ Router（FastAPI handlers）
```

`RequestSizeLimitMiddleware` 和 `ThrottleMiddleware` 自行调用 `problem_details_response()`，因此放在 ErrorHandler 内外对 413/429 的格式没有影响。`X-Request-Id` 是否附加取决于 `RequestIdMiddleware` 的位置。

---

## 省略某些 middleware 时

即使省略部分 middleware，其余的仍遵循相同的排序规则：

```python
# 省略 ThrottleMiddleware 和 RequestLoggingMiddleware 时
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
```

---

## 使用 ErrorHandlerMiddleware.install() 时

`install()` 同时执行 `add_middleware` 和 `add_exception_handler`，但仍需手动设置与其他 middleware 的相对顺序：

```python
# 先调用 install()（成为最内层）
ErrorHandlerMiddleware.install(app)          # 内层

# 然后添加其他 middleware
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)       # 外层
```

---

## 常见问题

**Q：`RequestSizeLimitMiddleware` 应该放在 ErrorHandler 内层还是外层？**

A：两者都可以，但放在 `RequestIdMiddleware` 内层意味着 413 响应也会带有 `X-Request-Id`。按上面推荐的顺序即可。

**Q：自定义 middleware 应该放在哪里？**

A：取决于 middleware 的性质：
- 需要添加到每个响应 → 紧接在 `RequestIdMiddleware` 之前（外层）
- 需要捕获 handler 异常 → 紧接在 `ErrorHandlerMiddleware` 之后（内层）
- 需要尽早拒绝请求 → 靠近 `RequestSizeLimitMiddleware` 或 `ThrottleMiddleware`
