"""Structural type contracts for UseCase and AsyncUseCase.

UseCaseProtocol — synchronous execute(input_) -> output
AsyncUseCaseProtocol — async execute(input_) -> output (awaitable)

Both use Python 3.12 generic syntax; any class with a matching
execute() signature satisfies them structurally (no inheritance needed).

Runtime isinstance() limitation
---------------------------------
Both protocols are @runtime_checkable, but Python's isinstance() only
checks that the ``execute`` attribute exists — it does NOT distinguish
between sync and async implementations. As a result:

    isinstance(sync_obj, AsyncUseCaseProtocol)  # → True (false positive)
    isinstance(async_obj, UseCaseProtocol)       # → True (false positive)

Static type safety (sync vs async) is guaranteed by mypy --strict, not
by isinstance() at runtime. If you need a runtime async check, use:

    import inspect
    inspect.iscoroutinefunction(obj.execute)

See ADR-0010 for the full rationale.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class UseCaseProtocol[I, O](Protocol):
    """Synchronous use-case contract.

    Warning: isinstance() only checks that ``execute`` exists, not whether
    it is synchronous. Use mypy --strict for compile-time enforcement, or
    ``not inspect.iscoroutinefunction(obj.execute)`` for a runtime check.
    """

    def execute(self, input_: I) -> O: ...


@runtime_checkable
class AsyncUseCaseProtocol[I, O](Protocol):
    """Asynchronous use-case contract — execute must be a coroutine.

    Warning: isinstance() only checks that ``execute`` exists, not whether
    it is async. Use mypy --strict for compile-time enforcement, or
    ``inspect.iscoroutinefunction(obj.execute)`` for a runtime check.
    """

    async def execute(self, input_: I) -> O: ...
