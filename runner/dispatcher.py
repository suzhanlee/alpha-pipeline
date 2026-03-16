"""
Multi-strategy dispatcher.

Runs several strategies in parallel over the same universe and returns
a side-by-side comparison. Used by the /api/compare endpoint.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from .backtest import run_backtest


async def run_comparison(
    strategies: list[str],
    kwargs: dict,
    data_path: str,
) -> dict:
    """
    Execute multiple strategies concurrently and aggregate results.

    ``kwargs`` may be either a flat dict (applied to all strategies, legacy) or
    a mapping of strategy name -> strategy-specific kwargs dict.

    Returns a dict with each strategy's metrics side-by-side.
    """
    def _get_kwargs(strategy: str) -> dict:
        if isinstance(kwargs.get(strategy), dict):
            # per-strategy mapping provided
            return kwargs[strategy]
        return kwargs  # legacy: single flat dict for all strategies

    tasks = [
        asyncio.create_task(
            run_backtest(str(uuid.uuid4()), strategy, _get_kwargs(strategy), data_path)
        )
        for strategy in strategies
    ]

    results: list[dict] = await asyncio.gather(*tasks)

    comparison: dict = {}
    for result in results:
        strategy_name = result.get("strategy", "unknown")
        comparison[strategy_name] = result

    return {
        "compared_at": datetime.utcnow().isoformat(),
        "strategies": comparison,
    }
