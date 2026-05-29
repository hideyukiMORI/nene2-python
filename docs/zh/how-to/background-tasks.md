# 操作指南：后台任务

使用 FastAPI 的 `BackgroundTasks` 在响应发送后运行后台工作。

---

## 1. 基本模式

```python
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

def send_notification(message: str) -> None:
    # 耗时操作（发送邮件、调用外部 API 等）
    print(f"Sending: {message}")

@app.post("/orders", status_code=201)
def create_order(
    body: CreateOrderBody,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    order = process_order(body)
    background_tasks.add_task(send_notification, f"Order {order.order_id} created")
    return JSONResponse({"order_id": order.order_id}, status_code=201)
```

---

## 2. 与 UseCase 保持分离

为保持 UseCase 与 HTTP 无关，不要将 `BackgroundTasks` 传入 UseCase。在 handler 层接收事件后，在那里添加到 BackgroundTasks 中。

```python
# ✅ UseCase 不感知 BackgroundTasks
class CreateOrderUseCase:
    def execute(self, body: CreateOrderInput) -> CreateOrderOutput:
        order = Order(...)
        return CreateOrderOutput(order_id=order.order_id, notify_email=body.email)

# 在 handler 层使用 BackgroundTasks
@app.post("/orders", status_code=201)
def create_order(
    body: CreateOrderBody,
    background_tasks: BackgroundTasks,
    use_case: CreateOrderUseCase = Depends(get_use_case),
) -> JSONResponse:
    result = use_case.execute(CreateOrderInput(email=body.email))
    background_tasks.add_task(send_notification, result.notify_email)
    return JSONResponse({"order_id": result.order_id}, status_code=201)
```

---

## 3. 在 TestClient 下的行为

在 `TestClient` 下，`BackgroundTasks` 在响应返回**之前**同步执行。

```python
executed: list[str] = []

def track_task(msg: str) -> None:
    executed.append(msg)

# 测试中 BackgroundTasks 同步执行
r = client.post("/orders", json={"email": "alice@example.com"})
assert r.status_code == 201
assert len(executed) == 1  # 已经执行完毕
```

在生产环境中，它在响应发送后异步执行；注意在测试中是同步的。

---

## 4. 失败不会导致 500

如果 `BackgroundTasks` 任务内部抛出异常，由于响应已经发送，不会产生 500 错误。该错误会被记录到日志。

```python
def risky_task() -> None:
    raise RuntimeError("Background task failed")

# 响应返回 201（后台错误被隐藏）
background_tasks.add_task(risky_task)
```

对于重要的工作，不要依赖 BackgroundTasks — 请使用任务队列（Celery、ARQ 等）。

---

## 5. 与 async def 结合使用

`background_tasks.add_task()` 同时接受同步和异步函数。

```python
async def async_notification(email: str) -> None:
    await send_email_async(email)

background_tasks.add_task(async_notification, user.email)
```
