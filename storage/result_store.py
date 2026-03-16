"""
Result persistence layer — Redis-backed.

Stores backtest results so both the API and worker containers
can read/write without sharing in-process memory.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from config import settings

logger = logging.getLogger(__name__)

_client: aioredis.Redis | None = None


async def _get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.REDIS_URL)
    return _client


async def save_result(run_id: str, result: dict[str, Any]) -> None:
    """Persist a backtest result to Redis."""
    client = await _get_client()

    serialised = {
        k: round(v, 2) if isinstance(v, float) else v
        for k, v in result.items()
    }

    await client.set(f"result:{run_id}", json.dumps(serialised), ex=86400)
    logger.debug("Saved result for %s", run_id)


async def get_result(run_id: str) -> dict[str, Any] | None:
    """Retrieve a stored result, or None if not found."""
    client = await _get_client()
    raw = await client.get(f"result:{run_id}")
    if raw is None:
        return None
    return json.loads(raw)
