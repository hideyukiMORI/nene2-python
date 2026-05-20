# FT86: Lifespan イベント — startup/shutdown とリソース共有パターン

**日付**: 2026-05-20  
**テーマ**: FastAPI lifespan context manager でのリソース初期化・クリーンアップと nene2 との共存  
**バージョン**: v1.8.29  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft86-lifespan/`

---

## 概要

FastAPI の `lifespan` パラメーターを使った起動時リソース初期化（DBプール、キャッシュ）と
`app.state` 経由でハンドラーへの注入パターンを検証。
nene2 の `setup_middlewares()` との共存は問題なし。
テスト時の `TestClient` の挙動と状態分離に摩擦あり。

---

## 実装パターン

### パターン: lifespan + app.state + Depends

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi import FastAPI, Depends, Request
from typing import Annotated

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # startup
    cache = InMemoryCache()
    db_pool = DatabasePool()
    db_pool.connect()
    app.state.cache = cache
    app.state.db_pool = db_pool

    yield  # アプリ実行

    # shutdown
    db_pool.disconnect()
    cache.clear()

app = FastAPI(lifespan=lifespan)
setup_middlewares(app)  # nene2 ミドルウェアと共存 ✅

# Depends でリソースを注入
def get_cache(request: Request) -> InMemoryCache:
    return request.app.state.cache  # type: ignore[return-value]

CacheDep = Annotated[InMemoryCache, Depends(get_cache)]

@app.get("/cache/{key}", response_model=CacheEntryResponse)
def get_entry(key: str, cache: CacheDep) -> JSONResponse:
    return JSONResponse({"key": key, "value": cache.get(key)})
```

---

## 発見した問題

### 問題1: TestClient の with ブロック必須が直感的でない

```python
# ❌ lifespan が実行されない — app.state.cache が未設定
client = TestClient(app)
client.get("/cache/greeting")  # → AttributeError → 500

# ✅ 正しい使い方
with TestClient(app) as client:
    client.get("/cache/greeting")  # → 200
```

`TestClient(app)` だけでは lifespan の startup が実行されない。
`with` ブロックで包む必要があるが、nene2 ドキュメントに記載がない。

### 問題2: テスト間の状態分離が保証されない

```python
# テスト A: with TestClient(app) を実行 → startup → app.state.cache が設定される
with TestClient(app) as client:
    ...  # startup が実行され app.state に値がセットされる

# テスト B: with なしで実行 → 前のテストの app.state.cache が残っている
client = TestClient(app)
client.get("/status")  # app.state が残っているため 200 になる（本来は 500 のはず）
```

pytest が同一プロセスで `app` モジュールを共有するため、
前のテストで設定された `app.state` が次のテストに引き継がれる。
テスト順序によって結果が変わる不安定なテストスイートになりやすい。

### 問題3: app.state の型安全性がない

```python
# mypy では Any になる
cache = request.app.state.cache  # type: ignore[return-value]
```

`Starlette.State` は動的アトリビューとを持つ `__slots__` なしのオブジェクト。
mypy は型を推論できず、`type: ignore` コメントが必要になる。

---

## テスト結果（全11件パス）

```
test_lifespan_startup_initializes_resources      PASSED
test_lifespan_cache_has_initial_value            PASSED
test_lifespan_cache_missing_key_returns_null     PASSED
test_lifespan_cache_set_and_get                  PASSED
test_lifespan_db_query_uses_pool                 PASSED
test_lifespan_db_query_count_increments          PASSED
test_lifespan_cache_shared_across_requests       PASSED
test_no_lifespan_status_returns_false            PASSED
test_friction_testclient_requires_with_block     PASSED
test_friction_app_state_no_type_safety           PASSED
test_friction_lifespan_error_handling            PASSED
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F86-1 | `TestClient` を `with` ブロックで使わないと lifespan が実行されず 500 になる | 高 |
| F86-2 | テスト間で `app.state` が引き継がれてテスト順序依存になる | 中 |
| F86-3 | `app.state` へのアクセスが型安全でなく `type: ignore` が必要 | 低 |

---

## 使用感（主観評価）

### 直感性 ★★☆☆☆

`lifespan` パラメーターと `yield` 境界は直感的だが、
TestClient の `with` ブロック必須は知らないとハマる。
「なぜ `client.get()` が 500 を返すのか」のデバッグに時間がかかる。
`AttributeError: 'State' object has no attribute 'cache'` が
nene2 の `ErrorHandlerMiddleware` に吸収されて 500 になるため
エラーメッセージが見えにくい（`APP_DEBUG=true` なら見える）。

### 実害の深刻さ ★★★★☆

テスト間の状態分離問題は CI で「時々落ちる」テストを生む。
テスト実行順序が変わった（pytest-randomly 導入、テスト追加）タイミングで
突然失敗するため、原因特定が難しい。

### 修正のしやすさ ★★★★☆

コード修正なし、ドキュメント追加のみで対応できる:
- how-to: `TestClient` を `with` ブロックで使う方法
- how-to: テスト間の状態分離のための `pytest.fixture` パターン
- how-to: `app.state` の型安全なアクセスパターン（typed wrapper）

### 総合コメント

lifespan + nene2 の組み合わせ自体は問題なく動く。
`setup_middlewares()` との共存も完全。
主な摩擦はテスト方法の周知不足であり、ドキュメントで解決できる。

---

## 推奨アクション

1. **docs**: how-to ガイドに「lifespan でリソースを管理する」記事を追加
   - `TestClient` は必ず `with` ブロックで使うことを明示
   - テスト間の状態分離パターン（`pytest.fixture` + `with TestClient`）
   - `app.state` の型安全なアクセスパターン（`get_or_raise` helper）
2. **docs**: nene2 example/ に lifespan パターンのサンプルを追加
