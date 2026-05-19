"""Database health check — verifies DB connectivity for /health endpoint."""

from nene2.http import HealthStatus

from .interfaces import DatabaseQueryExecutorInterface


class DatabaseHealthCheck:
    """Check database connectivity by executing a lightweight query."""

    def __init__(self, executor: DatabaseQueryExecutorInterface) -> None:
        self._executor = executor

    def check(self) -> HealthStatus:
        try:
            self._executor.fetch_one("SELECT 1 AS ok")
            return HealthStatus(status="ok", checks={"database": "ok"})
        except Exception:
            return HealthStatus(status="degraded", checks={"database": "error"})
