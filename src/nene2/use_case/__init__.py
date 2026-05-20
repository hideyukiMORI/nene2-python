"""UseCase contracts — synchronous and asynchronous Protocol definitions."""

from starlette.concurrency import run_in_threadpool

from .protocols import AsyncUseCaseProtocol, UseCaseProtocol

__all__ = ["AsyncUseCaseProtocol", "UseCaseProtocol", "run_in_threadpool"]
