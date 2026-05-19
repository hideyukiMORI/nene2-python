"""Structural type contracts for UseCase and AsyncUseCase.

UseCaseProtocol — synchronous execute(input_) -> output
AsyncUseCaseProtocol — async execute(input_) -> output (awaitable)

Both use Python 3.12 generic syntax; any class with a matching
execute() signature satisfies them structurally (no inheritance needed).
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class UseCaseProtocol[I, O](Protocol):
    """Synchronous use-case contract."""

    def execute(self, input_: I) -> O: ...


@runtime_checkable
class AsyncUseCaseProtocol[I, O](Protocol):
    """Asynchronous use-case contract — execute must be a coroutine."""

    async def execute(self, input_: I) -> O: ...
