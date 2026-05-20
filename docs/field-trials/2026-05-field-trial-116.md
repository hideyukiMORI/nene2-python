# Field Trial 116: @contextmanager リソース管理 + FastAPI lifespan

## テーマ

`@contextmanager` の `try/finally` でリソースのクリーンアップを保証しながら、
FastAPI の `lifespan` コンテキストマネージャと統合するパターンを検証する。
`FakeConnectionPool` を例に、接続の取得・返却・クローズが確実に行われることを確認する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft116-context-manager/` に以下を実装:

- `FakeConnectionPool` — 接続取得・返却・クローズをシミュレートする dataclass
- `managed_connection()` — `@contextmanager` + `try/finally` で接続のリークを防ぐ
- `lifespan()` — `@asynccontextmanager` で起動時にプール初期化、終了時にクローズ
- 8 テスト通過（修正後）

## テスト結果

3 件修正後、全 8 テスト通過。

## Friction Points

### FP1: `TestClient(app)` をコンテキストマネージャとして使わないと lifespan が起動しない

**状況**: `TestClient(app)` を直接インスタンス化してフィクスチャに渡すと、
lifespan の `startup` フェーズが実行されない。
`_pool` がグローバルで `None` のままなので 503 が返り続けた。

```python
# ❌ lifespan が実行されない
@pytest.fixture
def client() -> TestClient:
    return TestClient(app)  # startup イベントが起きない → _pool = None のまま

# ✅ コンテキストマネージャとして使う
@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c  # with ブロック開始で startup、終了で shutdown が実行される
```

**影響**: 中。lifespan を使うアプリでは必ず `with TestClient(app) as c:` パターンを使う必要がある。
FastAPI の公式ドキュメントに記載されているが、pytest フィクスチャでは見落としやすい。

## 観察

### O1: `@contextmanager` + `try/finally` で例外時も必ずリソースが返却される

```python
@contextmanager
def managed_connection(pool: FakeConnectionPool) -> Generator[str, None, None]:
    conn = pool.acquire()
    try:
        yield conn
    finally:
        pool.release(conn)  # 例外が発生しても必ず実行される
```

`try/finally` の `finally` ブロックは `yield` が例外で終了した場合も実行される。
接続リークを防ぐ確実な方法。

### O2: `@asynccontextmanager` で FastAPI lifespan を実装できる

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    pool = FakeConnectionPool(name="main-pool")
    try:
        yield
    finally:
        pool.close()

app = FastAPI(lifespan=lifespan)
```

`yield` 前が startup、`yield` 後（finally）が shutdown に対応する。
`app.on_event("startup")` の非推奨化に伴い、現在はこのパターンが標準。

### O3: ネストした `managed_connection` は独立して動作する

```python
with managed_connection(pool) as conn1:
    with managed_connection(pool) as conn2:
        assert pool.active_connections == 2
    assert pool.active_connections == 1
assert pool.active_connections == 0
```

内側の `with` ブロックが終了すると `conn2` が返却され、
外側が終了すると `conn1` が返却される。LIFO 順で確実に動作する。

## まとめ

FP1（TestClient をコンテキストマネージャとして使う）を how-to/lifespan-and-app-state.md に追記予定。
`@contextmanager` + lifespan の組み合わせは nene2 のデータベース接続管理パターンと一致しており、
一般的なリソース管理の基本として重要な確認が取れた。
