"""Database health check — verifies DB connectivity for /health endpoint."""

import logging

from nene2.http import HealthStatus

from .interfaces import DatabaseQueryExecutorInterface

logger = logging.getLogger(__name__)


class DatabaseHealthCheck:
    """Check database connectivity by executing a lightweight query."""

    def __init__(self, executor: DatabaseQueryExecutorInterface) -> None:
        self._executor = executor

    def check(self) -> HealthStatus:
        try:
            self._executor.fetch_one("SELECT 1 AS ok")
            return HealthStatus(status="ok", checks={"database": "ok"})
        except Exception as exc:
            logger.warning("database health check failed: %s", exc)
            return HealthStatus(status="error", checks={"database": "error"})
