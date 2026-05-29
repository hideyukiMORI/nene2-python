# How-to: BackgroundTasks

FastAPI の `BackgroundTasks` を使ってレスポンス後に処理を実行するパターンを説明する。

---

## 1. 基本パターン

```python
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

def send_notification(message: str) -> None:
    # 時間がかかる処理（メール送信・外部 API 呼び出し等）
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

## 2. UseCase との分離

UseCase を HTTP 非依存に保つため、`BackgroundTasks` は UseCase に渡さない。ハンドラー層でイベントを受け取り、BackgroundTasks に追加する。

```python
# ✅ UseCase は BackgroundTasks を知らない
class CreateOrderUseCase:
    def execute(self, body: CreateOrderInput) -> CreateOrderOutput:
        order = Order(...)
        return CreateOrderOutput(order_id=order.order_id, notify_email=body.email)

# ハンドラー層で BackgroundTasks を使う
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

## 3. TestClient での挙動

`TestClient` では `BackgroundTasks` がレスポンス返却 **前** に同期的に実行される。

```python
executed: list[str] = []

def track_task(msg: str) -> None:
    executed.append(msg)

# テストでは BackgroundTasks が同期実行される
r = client.post("/orders", json={"email": "alice@example.com"})
assert r.status_code == 201
assert len(executed) == 1  # すでに実行済み
```

本番環境では非同期実行（レスポンス後）だが、テストでは同期実行されることに注意。

---

## 4. 失敗しても 500 にならない

`BackgroundTasks` 内で例外が発生しても、レスポンスはすでに送信済みのため 500 にはならない。エラーはログに記録される。

```python
def risky_task() -> None:
    raise RuntimeError("Background task failed")

# レスポンスは 201 で返る（バックグラウンドエラーは隠れる）
background_tasks.add_task(risky_task)
```

重要な処理は BackgroundTasks に頼らず、ジョブキュー（Celery・ARQ 等）を使う。

---

## 5. async def との組み合わせ

`background_tasks.add_task()` には同期・非同期どちらの関数も渡せる。

```python
async def async_notification(email: str) -> None:
    await send_email_async(email)

background_tasks.add_task(async_notification, user.email)
```
