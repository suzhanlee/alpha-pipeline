"""
Backtest worker — separate process / container.

Consumes jobs from the Redis queue, executes backtests,
and stores results back in Redis.

Run locally:
    uv run python worker.py

Run via Docker:
    docker-compose up worker
"""

from __future__ import annotations

import asyncio
import logging

from mq.redis_queue import pop_job
from runner.backtest import run_backtest
from storage.result_store import save_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Worker started. Polling for jobs...")

    while True:
        job = await pop_job()

        if job is None:
            await asyncio.sleep(0.05)
            continue

        run_id = job["run_id"]
        strategy = job["strategy"]
        kwargs = job.get("kwargs", {})

        logger.info("Processing job %s (strategy=%s)", run_id, strategy)
        try:
            result = await run_backtest(run_id, strategy, kwargs)
            await save_result(run_id, result)
            logger.info("Job %s completed", run_id)
        except Exception as exc:
            logger.error("Job %s failed: %s", run_id, exc)
            await save_result(run_id, {"run_id": run_id, "error": str(exc), "status": "failed"})


if __name__ == "__main__":
    asyncio.run(main())
