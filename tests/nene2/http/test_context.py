"""RequestScopedContext のテスト。"""

import asyncio

import pytest

from nene2.http import RequestScopedContext


def test_set_and_get_returns_value() -> None:
    ctx: RequestScopedContext[str] = RequestScopedContext()
    ctx.set("hello")
    assert ctx.get() == "hello"


def test_get_or_none_returns_none_when_unset() -> None:
    ctx: RequestScopedContext[int] = RequestScopedContext()
    assert ctx.get_or_none() is None


def test_get_raises_lookup_error_when_unset() -> None:
    ctx: RequestScopedContext[int] = RequestScopedContext()
    with pytest.raises(LookupError):
        ctx.get()


def test_set_overwrites_previous_value() -> None:
    ctx: RequestScopedContext[int] = RequestScopedContext()
    ctx.set(1)
    ctx.set(2)
    assert ctx.get() == 2


def test_different_instances_are_independent() -> None:
    ctx_a: RequestScopedContext[str] = RequestScopedContext()
    ctx_b: RequestScopedContext[str] = RequestScopedContext()
    ctx_a.set("a")
    ctx_b.set("b")
    assert ctx_a.get() == "a"
    assert ctx_b.get() == "b"


def test_async_contexts_are_isolated() -> None:
    ctx: RequestScopedContext[str] = RequestScopedContext()
    results: list[str] = []

    async def task_a() -> None:
        ctx.set("request-a")
        await asyncio.sleep(0)
        results.append(ctx.get())

    async def task_b() -> None:
        ctx.set("request-b")
        await asyncio.sleep(0)
        results.append(ctx.get())

    async def run() -> None:
        await asyncio.gather(task_a(), task_b())

    asyncio.run(run())
    assert sorted(results) == ["request-a", "request-b"]


def test_none_value_stored_correctly() -> None:
    ctx: RequestScopedContext[str | None] = RequestScopedContext()
    ctx.set(None)
    assert ctx.get() is None
    assert ctx.get_or_none() is None
