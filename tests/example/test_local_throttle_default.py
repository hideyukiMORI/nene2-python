"""Local example app disables throttle by default (FT / dev ergonomics)."""

from fastapi.testclient import TestClient

from example.app import create_app
from nene2.config import AppSettings


def test_local_app_allows_burst_without_429() -> None:
    cfg = AppSettings(app_env="local")
    assert cfg.throttle_enabled is True  # settings default; create_app adjusts
    client = TestClient(create_app(cfg))
    for _ in range(30):
        r = client.get("/examples/ping")
        assert r.status_code == 200, r.text
