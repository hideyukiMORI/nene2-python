# 操作指南：领域事件模式

使用领域事件和 BackgroundTasks，将 UseCase 运行后的副作用（发送邮件、日志记录、通知）分离出来的模式。

---

## 1. 基本模式：使用 BackgroundTasks 异步运行事件

使用 FastAPI 的 `BackgroundTasks` 在响应后运行工作。

```python
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

def send_welcome_email(email: str) -> None:
    # 发送邮件（耗时操作）
    ...

@app.post("/users", status_code=201)
def create_user(body: CreateUserBody, background_tasks: BackgroundTasks) -> JSONResponse:
    user = create_user_use_case(body.name, body.email)
    background_tasks.add_task(send_welcome_email, user.email)
    return JSONResponse({"user_id": user.user_id}, status_code=201)
```

---

## 2. EventBus 模式：从 UseCase 发布领域事件

UseCase 发布事件，handler 订阅。UseCase 不感知 HTTP（不包含 BackgroundTasks）。

```python
from dataclasses import dataclass
from typing import Any, Callable

# 事件定义
@dataclass(frozen=True, slots=True)
class UserCreatedEvent:
    user_id: int
    email: str

# EventBus
type EventHandler = Callable[[Any], None]

class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = {}

    def subscribe(self, event_type: type, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: object) -> None:
        for handler in self._handlers.get(type(event), []):
            handler(event)

event_bus = EventBus()

# UseCase：与 HTTP 无关
class CreateUserUseCase:
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    def execute(self, name: str, email: str) -> User:
        user = User(...)
        self._event_bus.publish(UserCreatedEvent(user.user_id, user.email))
        return user

# 注册 handler
def on_user_created(event: UserCreatedEvent) -> None:
    send_welcome_email(event.email)

event_bus.subscribe(UserCreatedEvent, on_user_created)
```

---

## 3. 结合 BackgroundTasks 和 EventBus

在 HTTP handler 中使用 BackgroundTasks，在后台运行 EventBus handler。

```python
@app.post("/users", status_code=201)
def create_user(
    body: CreateUserBody,
    background_tasks: BackgroundTasks,
    use_case: CreateUserUseCase = Depends(get_create_user_use_case),
) -> JSONResponse:
    # UseCase 同步发布事件（在 EventBus 上排队）
    user = use_case.execute(body.name, body.email)
    # 通过 BackgroundTasks 在响应后运行 event handler
    for handler_call in collected_events:
        background_tasks.add_task(handler_call)
    return JSONResponse({"user_id": user.user_id}, status_code=201)
```

---

## 4. 在测试中验证事件

在 TestClient 下，BackgroundTasks 同步执行，不需要等待。

```python
# 在 TestClient 下，BackgroundTasks 在响应返回前同步执行
executed = []
event_bus.subscribe(UserCreatedEvent, lambda e: executed.append(e))

with TestClient(app) as client:
    r = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})

assert len(executed) == 1  # BackgroundTasks 已执行完毕
assert executed[0].email == "alice@example.com"
```

---

## 注意事项

- `EventBus` 容易成为模块级全局变量。如果 handler 在测试间积累，请用 `autouse` fixture 重置它。
- 在 UseCase 内部发布事件时，通过构造函数参数传入 `EventBus`（构造函数注入）— 避免直接引用全局变量。

---

## 5. dataclass 继承：有默认值的字段之后出现必填字段

如果基类有一个带 `default_factory` 的字段，在子类中添加必填字段会违反 Python dataclass 的规则。`kw_only=True`（Python 3.10+）可以解决这个问题。

```python
# ❌ 错误：'order_id' 是必填字段，出现在有默认值的 'occurred_at' 之后
@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str  # TypeError：非默认参数跟在默认参数后面

# ✅ 使用 kw_only=True 解决（Python 3.10+）
@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC), kw_only=True)

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str  # OK — kw_only 字段不受 MRO 顺序限制
    total_amount: int
```

使用 `kw_only=True` 后，该字段在 `__init__` 中成为仅限关键字参数。子类的必填参数可以定义为普通位置参数，`occurred_at` 则被视为可选参数。
