"""Protocol compliance tests for UseCaseProtocol and AsyncUseCaseProtocol."""

from nene2.use_case import AsyncUseCaseProtocol, UseCaseProtocol


class _SyncDouble:
    def execute(self, input_: int) -> str:
        return str(input_)


class _AsyncDouble:
    async def execute(self, input_: int) -> str:
        return str(input_)


class _BadDouble:
    def run(self, input_: int) -> str:
        return str(input_)


def test_sync_double_satisfies_use_case_protocol() -> None:
    assert isinstance(_SyncDouble(), UseCaseProtocol)


def test_async_double_satisfies_async_use_case_protocol() -> None:
    assert isinstance(_AsyncDouble(), AsyncUseCaseProtocol)


def test_bad_double_does_not_satisfy_use_case_protocol() -> None:
    assert not isinstance(_BadDouble(), UseCaseProtocol)


def test_bad_double_does_not_satisfy_async_use_case_protocol() -> None:
    assert not isinstance(_BadDouble(), AsyncUseCaseProtocol)


def test_runtime_isinstance_cannot_distinguish_sync_from_async() -> None:
    # @runtime_checkable only checks attribute presence, not coroutine type.
    # Sync/async distinction is enforced by mypy --strict, not at runtime.
    assert isinstance(_SyncDouble(), AsyncUseCaseProtocol)
