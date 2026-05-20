"""Tests for HealthCheckProtocol, HealthStatus, and CompositeHealthCheck."""

from nene2.http import CompositeHealthCheck, HealthCheckProtocol, HealthStatus


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
