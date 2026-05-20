"""Tests for run_in_threadpool re-export."""

import asyncio
import threading
import time

import pytest

from nene2.use_case import run_in_threadpool
from nene2.use_case import run_in_threadpool as _rtp_alias


def _sync_identity(value: int) -> int:
    return value


def _sync_slow(duration_s: float) -> str:
    time.sleep(duration_s)
    return "done"


def _sync_raises() -> None:
    raise ValueError("boom")


def test_run_in_threadpool_returns_value() -> None:
    result = asyncio.run(run_in_threadpool(_sync_identity, 42))
    assert result == 42


def test_run_in_threadpool_runs_in_thread() -> None:
    """sync 関数が呼び出し元スレッドとは別スレッドで実行される。"""
    caller_thread = threading.current_thread().ident

    def _get_thread_id() -> int | None:
        return threading.current_thread().ident

    thread_id = asyncio.run(run_in_threadpool(_get_thread_id))
    assert thread_id != caller_thread


async def test_run_in_threadpool_does_not_block_event_loop() -> None:
    """並行して 3 つの 100ms スリープをオフロードし、合計が ~100ms になることを確認。"""
    t0 = time.perf_counter()
    await asyncio.gather(
        run_in_threadpool(_sync_slow, 0.1),
        run_in_threadpool(_sync_slow, 0.1),
        run_in_threadpool(_sync_slow, 0.1),
    )
    elapsed = time.perf_counter() - t0
    # 順次なら 0.3s、並列なら ~0.1s — 0.25s 未満ならスレッドプール並列化が効いている
    assert elapsed < 0.25


async def test_run_in_threadpool_propagates_exception() -> None:
    with pytest.raises(ValueError, match="boom"):
        await run_in_threadpool(_sync_raises)


def test_run_in_threadpool_is_importable_from_nene2_use_case() -> None:
    assert callable(_rtp_alias)
