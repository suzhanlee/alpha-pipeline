"""
Backtest orchestrator.

Runs a strategy over the full universe and aggregates results.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import pandas as pd

from config import settings
from data import load_price_data, get_universe
from metrics import compute_metrics
from strategy import get_strategy
from .progress import emit

logger = logging.getLogger(__name__)

async def run_backtest(
    run_id: str,
    strategy_name: str,
    strategy_kwargs: dict | None = None,
    data_path: str = settings.DATA_PATH,
) -> dict:
    """
    Execute a full backtest and return performance metrics.

    Steps
    -----
    1. Load price data
    2. Resolve tradeable universe
    3. For each ticker: run strategy, compute per-ticker metrics
    4. Aggregate into equal-weight portfolio returns
    5. Compute portfolio-level metrics
    """
    strategy_kwargs = strategy_kwargs or {}
    _ticker_returns: list[pd.Series] = []

    await emit(run_id, "loading_data", 5)
    loop = asyncio.get_event_loop()
    df = load_price_data(data_path)

    await emit(run_id, "building_universe", 15)
    universe = get_universe(df)
    if not universe:
        raise RuntimeError("Empty universe — check data file.")
    logger.info("Universe: %s", universe)

    _ticker_returns = []
    n = len(universe)

    for i, ticker in enumerate(universe):
        pct = 15 + int((i / n) * 70)
        await emit(run_id, "running_strategy", pct, ticker=ticker)

        ticker_df = df.xs(ticker, level="ticker").copy()
        strategy = get_strategy(strategy_name, **strategy_kwargs)

        result_df = await loop.run_in_executor(None, strategy.compute, ticker_df)
        _ticker_returns.append(result_df["strategy_return"].rename(ticker))

    await emit(run_id, "computing_metrics", 90)

    # Equal-weight portfolio: average daily return across tickers
    portfolio = pd.concat(_ticker_returns, axis=1).mean(axis=1).dropna()
    portfolio.name = "portfolio"

    metrics = compute_metrics(portfolio, risk_free_rate=settings.RISK_FREE_RATE_ANNUAL)

    await emit(run_id, "complete", 100)

    return {
        "run_id": run_id,
        "strategy": strategy_name,
        "universe": universe,
        "period": {
            "start": str(portfolio.index.min().date()),
            "end": str(portfolio.index.max().date()),
        },
        "computed_at": datetime.utcnow().isoformat(),
        **metrics,
    }
