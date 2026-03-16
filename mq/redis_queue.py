"""
Redis-backed job queue.

The API service pushes backtest jobs here.
The worker service pops and executes them.

This mirrors a production message-queue pattern (e.g. Redis Streams, RabbitMQ)
where the API and worker run as separate processes / containers.
"""

from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis

from config import settings

logger = logging.getLogger(__name__)

QUEUE_KEY = "backtest:jobs"

_client: aioredis.Redis | None = None


async def _get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.REDIS_URL)
    return _client


async def push_job(run_id: str, strategy: str, kwargs: dict) -> None:
    """Enqueue a backtest job."""
    client = await _get_client()
    payload = json.dumps({"run_id": run_id, "strategy": strategy, "kwargs": kwargs})
    await client.lpush(QUEUE_KEY, payload)
    logger.debug("Enqueued job %s", run_id)


async def pop_job() -> dict | None:
    """
    Pop the next job from the queue.

    Returns None if the queue is empty.
    """
    client = await _get_client()
    raw = await client.rpop(QUEUE_KEY)
    if raw is None:
        return None
    return json.loads(raw)
