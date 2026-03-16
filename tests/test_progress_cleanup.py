"""Tests that progress state is cleaned up after completion."""
import asyncio
import pytest
from runner.progress import emit, _state


@pytest.mark.asyncio
async def test_progress_state_deleted_on_complete():
    """M-5: After emitting 'complete', the run_id entry must be removed from _state."""
    run_id = "test-cleanup-run-001"

    # Emit some progress events
    await emit(run_id, "processing", 50, ticker="AAPL")
    assert run_id in _state, "State should exist after progress emit"

    # Emit complete
    await emit(run_id, "complete", 100)

    # State should be cleaned up
    assert run_id not in _state, (
        f"Memory leak: run_id '{run_id}' still in _state after complete event. "
        f"Current state keys: {list(_state.keys())}"
    )


@pytest.mark.asyncio
async def test_progress_non_complete_events_keep_state():
    """M-5: Non-complete events should still store state."""
    run_id = "test-cleanup-run-002"

    await emit(run_id, "processing", 25, ticker="MSFT")
    assert run_id in _state

    await emit(run_id, "processing", 75, ticker="GOOG")
    assert run_id in _state

    # Cleanup
    if run_id in _state:
        del _state[run_id]
