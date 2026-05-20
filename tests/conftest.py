"""Root conftest — session-level teardown for module-level singletons."""

from collections.abc import Generator

import pytest

from example.app import app as _module_app
from nene2.database import SqlAlchemyQueryExecutor
from nene2.log import configure_for_testing

configure_for_testing()


@pytest.fixture(scope="session", autouse=True)
def _dispose_module_app() -> Generator[None, None, None]:
    """Dispose the module-level app engine to suppress ResourceWarning on shutdown."""
    yield
    executor = getattr(_module_app.state, "db_executor", None)
    if isinstance(executor, SqlAlchemyQueryExecutor):
        executor.engine.dispose()
