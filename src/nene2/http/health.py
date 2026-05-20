"""HealthCheckProtocol, HealthStatus, and CompositeHealthCheck."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class HealthStatus:
    status: str
    checks: dict[str, str] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.status == "ok"

    @property
    def http_status_code(self) -> int:
        return 200 if self.is_healthy else 503


@runtime_checkable
class HealthCheckProtocol(Protocol):
    """Contract for application health checks."""

    def check(self) -> HealthStatus: ...


class CompositeHealthCheck:
    """Aggregate multiple :class:`HealthCheckProtocol` instances into one.

    Returns ``HealthStatus(status="ok")`` only when all checks pass.
    Any failing check sets the overall status to ``"error"``::

        from nene2.http import CompositeHealthCheck

        composite = CompositeHealthCheck([db_check, external_api_check])
        status = composite.check()
        # HealthStatus(status="ok", checks={"database": "ok", "external_api": "ok"})
    """

    def __init__(self, checks: list[HealthCheckProtocol]) -> None:
        self._checks = checks

    def check(self) -> HealthStatus:
        merged: dict[str, str] = {}
        overall = "ok"
        for health_check in self._checks:
            result = health_check.check()
            merged.update(result.checks)
            if not result.is_healthy:
                overall = "error"
        return HealthStatus(status=overall, checks=merged)
