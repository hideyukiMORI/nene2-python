# How-to: ドメインイベントパターン

UseCase 実行後のサイドエフェクト（メール送信・ログ・通知）を、ドメインイベントと BackgroundTasks で分離するパターンを説明する。

---

## 1. 基本パターン: BackgroundTasks でイベントを非同期実行

FastAPI の `BackgroundTasks` でレスポンス後に処理を実行する。

```python
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

def send_welcome_email(email: str) -> None:
    # メール送信処理（時間がかかる）
    ...

@app.post("/users", status_code=201)
def create_user(body: CreateUserBody, background_tasks: BackgroundTasks) -> JSONResponse:
    user = create_user_use_case(body.name, body.email)
    background_tasks.add_task(send_welcome_email, user.email)
    return JSONResponse({"user_id": user.user_id}, status_code=201)
```

---

## 2. EventBus パターン: UseCase からドメインイベントを発行

UseCase がイベントを発行し、ハンドラーが購読するパターン。UseCase は HTTP 知識（BackgroundTasks）を持たない。

```python
from dataclasses import dataclass
from typing import Any, Callable

# イベント定義
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

# UseCase: HTTP 非依存
class CreateUserUseCase:
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    def execute(self, name: str, email: str) -> User:
        user = User(...)
        self._event_bus.publish(UserCreatedEvent(user.user_id, user.email))
        return user

# ハンドラー登録
def on_user_created(event: UserCreatedEvent) -> None:
    send_welcome_email(event.email)

event_bus.subscribe(UserCreatedEvent, on_user_created)
```

---

## 3. BackgroundTasks と EventBus の組み合わせ

HTTP ハンドラーで BackgroundTasks を使い、EventBus のハンドラーをバックグラウンドで実行する。

```python
@app.post("/users", status_code=201)
def create_user(
    body: CreateUserBody,
    background_tasks: BackgroundTasks,
    use_case: CreateUserUseCase = Depends(get_create_user_use_case),
) -> JSONResponse:
    # UseCase はイベントを同期発行（EventBus に積む）
    user = use_case.execute(body.name, body.email)
    # BackgroundTasks でイベント処理をレスポンス後に実行
    for handler_call in collected_events:
        background_tasks.add_task(handler_call)
    return JSONResponse({"user_id": user.user_id}, status_code=201)
```

---

## 4. テストでのイベント確認

テスト時は BackgroundTasks の実行を待たずに完了するため、TestClient では同期的にすぐ実行される。

```python
# TestClient では BackgroundTasks がレスポンス返却前に同期実行される
executed = []
event_bus.subscribe(UserCreatedEvent, lambda e: executed.append(e))

with TestClient(app) as client:
    r = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})

assert len(executed) == 1  # BackgroundTasks は完了済み
assert executed[0].email == "alice@example.com"
```

---

## 注意点

- `EventBus` はモジュールレベルのグローバル変数になりやすい。テスト間でハンドラーが蓄積する場合は `autouse` fixture でリセットする。
- UseCase 内でイベントを発行する場合、UseCase の引数に `EventBus` を渡してコンストラクタインジェクションする（グローバル参照を避ける）。
