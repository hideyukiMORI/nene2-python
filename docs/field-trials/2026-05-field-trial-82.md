# FT82: Background Tasks — FastAPI BackgroundTasks と nene2 の組み合わせ

**日付**: 2026-05-20  
**テーマ**: FastAPI BackgroundTasks を nene2 アーキテクチャと組み合わせた際の動作とパターン検証  
**バージョン**: v1.8.27  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft82-background-tasks/`

---

## 概要

FastAPI の `BackgroundTasks` は「レスポンス返却後に処理を実行する」仕組みで、
メール送信・在庫更新・監査ログなどのユースケースに使う。
nene2 のミドルウェアスタック（`setup_middlewares()`）との共存、
例外ハンドリングの限界、UseCase への注入パターンを検証した。

---

## 実装パターン

### 基本パターン（ハンドラーで BackgroundTasks を受け取る）

```python
from fastapi import BackgroundTasks

@app.post("/orders")
def create_order(body: OrderBody, background_tasks: BackgroundTasks) -> JSONResponse:
    output = use_case.execute(CreateOrderInput(item=body.item, quantity=body.quantity))
    # レスポンス送信後にバックグラウンドで実行される
    background_tasks.add_task(send_order_confirmation, output.order_id, output.item)
    background_tasks.add_task(update_inventory, output.item, output.quantity)
    return JSONResponse({...}, status_code=201)
```

### UseCase を注入可能にするパターン（テスト用ファクトリー）

```python
def create_app_with_use_case(
    create_order_fn: Callable[[CreateOrderInput], CreateOrderOutput]
) -> FastAPI:
    factory_app = FastAPI()
    setup_middlewares(factory_app)

    @factory_app.post("/orders")
    def _create_order(body: OrderBody, background_tasks: BackgroundTasks) -> JSONResponse:
        output = create_order_fn(...)
        background_tasks.add_task(send_order_confirmation, output.order_id, output.item)
        return JSONResponse({...}, status_code=201)

    return factory_app

# テストでの使用
injected_app = create_app_with_use_case(lambda _: mock_output)
```

---

## 発見した問題

### 問題1: バックグラウンドタスクの例外がクライアントに見えない

```python
# バックグラウンドタスクが例外を投げても...
def send_email(order_id: int) -> None:
    raise SMTPConnectionError("Mail server down")

@app.post("/orders")
def create_order(body: OrderBody, background_tasks: BackgroundTasks) -> JSONResponse:
    output = use_case.execute(...)
    background_tasks.add_task(send_email, output.order_id)
    return JSONResponse({...}, status_code=201)  # ← 201 が返る

# クライアントには 201 が届く（メール失敗は見えない）
```

FastAPI の設計上、レスポンスはすでに送信済みのため
バックグラウンドタスクのエラーを HTTP レスポンスコードで伝えられない。
エラーはサーバーログに記録されるが、クライアントには `201 Created` が届く。

### 問題2: nene2 に BackgroundTasks 推奨パターンがない

```python
# UseCase にどうやって BackgroundTasks を渡すか、ドキュメントがない

# ❌ UseCase の中で直接 BackgroundTasks を使う（アーキテクチャ違反）
class CreateOrderUseCase:
    def execute(self, input_: CreateOrderInput, bg: BackgroundTasks) -> CreateOrderOutput:
        ...
        bg.add_task(send_email, ...)  # UseCase が HTTP 境界に依存してしまう

# ✅ ハンドラー層で BackgroundTasks を使い、UseCase は純粋に保つ
@app.post("/orders")
def create_order(body: OrderBody, background_tasks: BackgroundTasks) -> JSONResponse:
    output = use_case.execute(CreateOrderInput(...))  # UseCase はクリーン
    background_tasks.add_task(send_email, output.order_id)  # ハンドラー層で副作用
    return JSONResponse({...})
```

正しいパターン（UseCase を純粋に保ちハンドラー層で BackgroundTasks を使う）が
nene2 のドキュメントに記載されていない。

### 問題3: バックグラウンドタスクの実行確認ができない

```python
# 「タスクをキューした」ことと「タスクが成功した」ことを HTTP で区別できない
r = client.post("/orders/1/alert")
# レスポンスは {"queued": True} — 成功したかどうかはわからない
```

本番運用では Celery・ARQ・FastAPI Scheduler などの外部ジョブキューが必要。
「BackgroundTasks は軽量な one-shot 処理向け」という点がドキュメントに不足。

---

## テスト結果（全16件パス）

```
test_create_order_returns_201                              PASSED
test_get_order_returns_200                                 PASSED
test_get_nonexistent_order_returns_404                     PASSED
test_background_tasks_execute_after_response               PASSED  # TestClient は同期実行
test_multiple_background_tasks_all_execute                 PASSED
test_background_task_with_alert                            PASSED
test_background_task_not_queued_on_404                     PASSED  # 404 ではタスク未実行
test_failing_background_task_does_not_affect_response      PASSED  # 例外 → 200 のまま
test_failing_background_task_started                       PASSED
test_request_id_present_with_background_tasks              PASSED  # nene2 と共存
test_security_headers_present_with_background_tasks        PASSED  # nene2 と共存
test_validation_error_does_not_queue_background_tasks      PASSED  # 422 では未実行
test_injectable_use_case_pattern                           PASSED  # DI パターン動作
test_friction_background_exception_not_visible_to_client   PASSED  # 摩擦記録
test_friction_no_nene2_background_task_pattern             PASSED  # 摩擦記録
test_friction_background_task_cannot_return_result         PASSED  # 摩擦記録
```

---

## 重要な発見: TestClient はバックグラウンドタスクを同期実行する

```python
client = TestClient(app)
r = client.post("/orders", json={"item": "Widget", "quantity": 1})
# TestClient はレスポンスを返す前にバックグラウンドタスクも実行する
assert "confirmation:order_1:Widget" in notification_log  # ✅ すでに実行済み
```

`TestClient` はバックグラウンドタスクをリクエスト完了前に同期的に実行するため、
テストでは `background_tasks.add_task()` で追加した処理を即座に検証できる。

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F82-1 | バックグラウンドタスクの例外がクライアントに見えない（FastAPI 設計上の制約） | 中 |
| F82-2 | nene2 に BackgroundTasks 推奨パターン（UseCase との分離）のドキュメントがない | 低 |
| F82-3 | バックグラウンドタスクは result を返せない（外部キューが必要） | 低 |

---

## 使用感（主観評価）

### 直感性 ★★★★☆

`background_tasks.add_task(fn, arg1, arg2)` は非常にシンプルで直感的。
FastAPI のドキュメントを読めば即座に使える。
nene2 のミドルウェアスタックとの共存も問題なし。

### 実害の深刻さ ★★☆☆☆

バックグラウンド例外がクライアントに見えない問題は、
軽量な通知タスク（メール送信）であれば許容範囲。
ただし「注文確定」のような業務的に重要な処理を
バックグラウンドタスクに入れるのは設計ミス — そこは UseCase に残すべき。

### 修正のしやすさ ★★★★★

必要なのはドキュメントのみ:
- UseCase はクリーンに保つ（BackgroundTasks を引数に取らない）
- ハンドラー層でのみ `background_tasks.add_task()` を呼ぶ
- 失敗して困る処理はバックグラウンドタスクに入れない
- TestClient はバックグラウンドタスクを同期実行する（テスト性良好）

### 総合コメント

FastAPI の `BackgroundTasks` は nene2 と相性が良く、
`setup_middlewares()` のミドルウェアスタックとも完全に共存する。
X-Request-Id・セキュリティヘッダーも正常に付与される。
摩擦の大部分は「どう使うべきか」のドキュメント不足であり、
フレームワークの改修は不要。

---

## 推奨アクション

1. **docs**: BackgroundTasks パターン（UseCase との分離、TestClient の同期実行）を how-to ガイドに追加
2. **minor**: BackgroundTasks は「失敗しても OK な副作用のみ」というガイドラインの明記
