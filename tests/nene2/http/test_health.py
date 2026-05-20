"""Tests for HealthCheckProtocol, HealthStatus, and CompositeHealthCheck."""

import asyncio
import time

from nene2.http import (
    AsyncCompositeHealthCheck,
    AsyncHealthCheckProtocol,
    CompositeHealthCheck,
    HealthCheckProtocol,
    HealthStatus,
)


class _OkCheck:
    def check(self) -> HealthStatus:
        return HealthStatus(status="ok", checks={"service_a": "ok"})


class _ErrorCheck:
    def check(self) -> HealthStatus:
        return HealthStatus(status="error", checks={"service_b": "error"})


def test_health_status_is_healthy_when_ok() -> None:
    assert HealthStatus(status="ok").is_healthy is True


def test_health_status_is_not_healthy_when_error() -> None:
    assert HealthStatus(status="error").is_healthy is False


def test_composite_returns_ok_when_all_checks_pass() -> None:
    class _OkCheck2:
        def check(self) -> HealthStatus:
            return HealthStatus(status="ok", checks={"service_b": "ok"})

    composite = CompositeHealthCheck([_OkCheck(), _OkCheck2()])
    result = composite.check()
    assert result.is_healthy is True
    assert result.status == "ok"


def test_composite_returns_error_when_any_check_fails() -> None:
    composite = CompositeHealthCheck([_OkCheck(), _ErrorCheck()])
    result = composite.check()
    assert result.is_healthy is False
    assert result.status == "error"


def test_composite_merges_all_checks() -> None:
    composite = CompositeHealthCheck([_OkCheck(), _ErrorCheck()])
    result = composite.check()
    assert "service_a" in result.checks
    assert "service_b" in result.checks


def test_composite_satisfies_protocol() -> None:
    composite = CompositeHealthCheck([_OkCheck()])
    assert isinstance(composite, HealthCheckProtocol)


def test_composite_with_empty_checks_returns_ok() -> None:
    composite = CompositeHealthCheck([])
    result = composite.check()
    assert result.is_healthy is True
    assert result.checks == {}


def test_health_status_http_status_code_ok() -> None:
    assert HealthStatus(status="ok").http_status_code == 200


def test_health_status_http_status_code_error() -> None:
    assert HealthStatus(status="error").http_status_code == 503


class _AsyncOkCheck:
    async def check(self) -> HealthStatus:
        return HealthStatus(status="ok", checks={"async_a": "ok"})


class _AsyncErrorCheck:
    async def check(self) -> HealthStatus:
        return HealthStatus(status="error", checks={"async_b": "error"})


async def test_async_composite_returns_ok_when_all_pass() -> None:
    class _AsyncOkCheck2:
        async def check(self) -> HealthStatus:
            return HealthStatus(status="ok", checks={"async_b": "ok"})

    composite = AsyncCompositeHealthCheck([_AsyncOkCheck(), _AsyncOkCheck2()])
    result = await composite.check()
    assert result.is_healthy is True
    assert result.status == "ok"
    assert "async_a" in result.checks
    assert "async_b" in result.checks


async def test_async_composite_returns_error_when_any_fails() -> None:
    composite = AsyncCompositeHealthCheck([_AsyncOkCheck(), _AsyncErrorCheck()])
    result = await composite.check()
    assert result.is_healthy is False
    assert result.status == "error"


async def test_async_composite_with_empty_checks_returns_ok() -> None:
    composite = AsyncCompositeHealthCheck([])
    result = await composite.check()
    assert result.is_healthy is True
    assert result.checks == {}


def test_async_health_check_satisfies_protocol() -> None:
    assert isinstance(_AsyncOkCheck(), AsyncHealthCheckProtocol)


async def test_async_composite_runs_checks_concurrently() -> None:
    call_order: list[str] = []

    class _SlowCheck:
        async def check(self) -> HealthStatus:
            await asyncio.sleep(0.05)
            call_order.append("slow")
            return HealthStatus(status="ok", checks={"slow": "ok"})

    class _FastCheck:
        async def check(self) -> HealthStatus:
            call_order.append("fast")
            return HealthStatus(status="ok", checks={"fast": "ok"})

    start = time.monotonic()
    composite = AsyncCompositeHealthCheck([_SlowCheck(), _FastCheck()])
    await composite.check()
    elapsed = time.monotonic() - start
    # 並列実行なので 2 * 0.05 秒よりずっと短い
    assert elapsed < 0.09
    assert set(call_order) == {"slow", "fast"}
