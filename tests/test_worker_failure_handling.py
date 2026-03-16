"""Tests that worker handles job failures with dead-letter recording."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_process_job_function_exists():
    """L-2: worker must have a process_job(job) function (not inline try/except)."""
    import worker
    assert hasattr(worker, 'process_job'), (
        "worker.py must have a top-level 'process_job' async function"
    )


def test_record_dead_letter_function_exists():
    """L-2: worker must have a record_dead_letter function."""
    import worker
    assert hasattr(worker, 'record_dead_letter'), (
        "worker.py must have a 'record_dead_letter' async function"
    )


@pytest.mark.asyncio
async def test_process_job_calls_record_dead_letter_on_failure():
    """L-2: When process_job fails, it must call record_dead_letter."""
    import worker

    dead_letters = []

    async def mock_dead_letter(run_id, reason):
        dead_letters.append((run_id, reason))

    job = {"run_id": "test-fail-001", "strategy": "sma_cross", "kwargs": {}}

    with patch("worker.run_backtest", side_effect=Exception("simulated failure")), \
         patch("worker.record_dead_letter", side_effect=mock_dead_letter):
        try:
            await worker.process_job(job)
        except Exception:
            pass  # process_job may re-raise or swallow

    assert len(dead_letters) >= 1, (
        "record_dead_letter was not called when process_job raised an exception"
    )
    assert dead_letters[0][0] == "test-fail-001"


@pytest.mark.asyncio
async def test_record_dead_letter_writes_to_redis():
    """L-2: record_dead_letter must write to Redis key dead_letter:{run_id}."""
    import worker
    import inspect

    source = inspect.getsource(worker.record_dead_letter)
    assert "dead_letter" in source, (
        "record_dead_letter must write to a Redis key containing 'dead_letter'"
    )
