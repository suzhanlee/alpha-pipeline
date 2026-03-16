"""
Async job queue for backtest dispatch.

Decouples the HTTP layer from backtest execution — the API enqueues jobs
and a background worker consumes them. Mirrors a message-queue pattern
(e.g. RabbitMQ, Redis Streams) that would be used when scaling to multiple
worker processes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

_queue: asyncio.Queue = asyncio.Queue()


async def enqueue_job(run_id: str, strategy: str, kwargs: dict) -> None:
    """Add a backtest job to the queue."""
    await _queue.put({"run_id": run_id, "strategy": strategy, "kwargs": kwargs})


def start_worker(execute_fn: Callable[..., Awaitable[None]]) -> None:
    """
    Spawn a background worker that consumes jobs from the queue.

    Call once at application startup (lifespan).
    """
    asyncio.create_task(_consume(execute_fn))


async def _consume(execute_fn: Callable[..., Awaitable[None]]) -> None:
    """Continuously drain the job queue."""
    while True:
        job = await _queue.get()
        try:
            await execute_fn(job["run_id"], job["strategy"], job["kwargs"])
        except Exception:
            pass
