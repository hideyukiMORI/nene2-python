"""HealthCheckProtocol and HealthStatus — framework health check contract."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class HealthStatus:
    status: str
    checks: dict[str, str] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.status == "ok"


class HealthCheckProtocol(Protocol):
    """Contract for application health checks."""

    def check(self) -> HealthStatus: ...
