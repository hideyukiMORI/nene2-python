"""Tests for ThrottleMiddleware / InMemoryRateLimitStorage / RateLimitStorageProtocol."""

import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.middleware import InMemoryRateLimitStorage, RateLimitStorageProtocol, ThrottleMiddleware


def _make_app(limit: int = 3, window: int = 60) -> FastAPI:
    app = FastAPI()
    app.add_middleware(ThrottleMiddleware, limit=limit, window=window)

    @app.get("/ping")
    async def ping() -> JSONResponse:
        return JSONResponse({"ok": True})

    return app


def test_requests_within_limit_pass() -> None:
    client = TestClient(_make_app(limit=5))
    for _ in range(5):
        assert client.get("/ping").status_code == 200


def test_requests_exceeding_limit_return_429() -> None:
    client = TestClient(_make_app(limit=2))
    client.get("/ping")
    client.get("/ping")
    response = client.get("/ping")
    assert response.status_code == 429
    body = response.json()
    assert body["type"].endswith("too-many-requests")
    assert "Retry-After" in response.headers


def test_forwarded_for_header_used_as_key() -> None:
    client = TestClient(_make_app(limit=1))
    client.get("/ping", headers={"X-Forwarded-For": "10.0.0.1"})
    response = client.get("/ping", headers={"X-Forwarded-For": "10.0.0.1"})
    assert response.status_code == 429

    response2 = client.get("/ping", headers={"X-Forwarded-For": "10.0.0.2"})
    assert response2.status_code == 200


def test_exclude_paths_bypasses_throttle() -> None:
    app = FastAPI()
    app.add_middleware(
        ThrottleMiddleware,
        limit=2,
        window=60,
        exclude_paths=["/health"],
    )

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/ping")
    async def ping() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    for _ in range(5):
        assert client.get("/health").status_code == 200

    client.get("/ping")
    client.get("/ping")
    assert client.get("/ping").status_code == 429


def test_exclude_paths_default_is_empty() -> None:
    client = TestClient(_make_app(limit=1))
    client.get("/ping")
    assert client.get("/ping").status_code == 429


def test_successful_response_includes_rate_limit_headers() -> None:
    client = TestClient(_make_app(limit=5))
    r = client.get("/ping")
    assert r.status_code == 200
    assert r.headers["X-RateLimit-Limit"] == "5"
    assert r.headers["X-RateLimit-Remaining"] == "4"
    assert "X-RateLimit-Reset" in r.headers


def test_rate_limit_remaining_decrements_per_request() -> None:
    client = TestClient(_make_app(limit=5))
    r1 = client.get("/ping")
    r2 = client.get("/ping")
    assert int(r1.headers["X-RateLimit-Remaining"]) > int(r2.headers["X-RateLimit-Remaining"])


def test_429_response_includes_rate_limit_headers() -> None:
    client = TestClient(_make_app(limit=2))
    client.get("/ping")
    client.get("/ping")
    r = client.get("/ping")
    assert r.status_code == 429
    assert r.headers["X-RateLimit-Limit"] == "2"
    assert r.headers["X-RateLimit-Remaining"] == "0"
    assert "X-RateLimit-Reset" in r.headers
    assert "Retry-After" in r.headers


def test_path_limits_override_default_limit() -> None:
    app = FastAPI()
    app.add_middleware(
        ThrottleMiddleware,
        limit=100,
        window=60,
        path_limits={"/expensive": 2},
    )

    @app.get("/expensive")
    async def expensive() -> JSONResponse:
        return JSONResponse({"ok": True})

    @app.get("/cheap")
    async def cheap() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    assert client.get("/expensive").status_code == 200
    assert client.get("/expensive").status_code == 200
    assert client.get("/expensive").status_code == 429
    # cheap は path_limits に含まれないので 100 req まで許可
    assert client.get("/cheap").status_code == 200


def test_path_limit_and_default_limit_are_independent_counters() -> None:
    app = FastAPI()
    app.add_middleware(
        ThrottleMiddleware,
        limit=2,
        window=60,
        path_limits={"/special": 1},
    )

    @app.get("/special")
    async def special() -> JSONResponse:
        return JSONResponse({"ok": True})

    @app.get("/normal")
    async def normal() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    # /special: limit=1
    assert client.get("/special").status_code == 200
    assert client.get("/special").status_code == 429
    # /normal: limit=2 (別カウンター)
    assert client.get("/normal").status_code == 200
    assert client.get("/normal").status_code == 200
    assert client.get("/normal").status_code == 429


def test_path_limit_reflected_in_x_ratelimit_limit_header() -> None:
    app = FastAPI()
    app.add_middleware(ThrottleMiddleware, limit=100, window=60, path_limits={"/ping": 5})

    @app.get("/ping")
    async def ping() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    r = client.get("/ping")
    assert r.headers["X-RateLimit-Limit"] == "5"


def test_stale_entries_are_evicted_after_window_expires() -> None:
    storage = InMemoryRateLimitStorage()
    now = time.monotonic()
    for i in range(10):
        storage.acquire(f"192.168.1.{i}", now, 1.0)

    assert len(storage._counts) == 10

    time.sleep(1.1)

    # 新しいリクエストでクリーンアップがトリガーされる
    storage.acquire("10.0.0.99", time.monotonic(), 1.0)

    # 古い 10 エントリは削除され、新しい 1 エントリのみ残る
    assert len(storage._counts) == 1


def test_custom_storage_is_used_by_throttle_middleware() -> None:
    storage = InMemoryRateLimitStorage()
    app = FastAPI()
    app.add_middleware(ThrottleMiddleware, limit=2, window=60, storage=storage)

    @app.get("/ping")
    async def ping() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 429


def test_rate_limit_storage_protocol_is_satisfied() -> None:
    storage = InMemoryRateLimitStorage()
    assert isinstance(storage, RateLimitStorageProtocol)
