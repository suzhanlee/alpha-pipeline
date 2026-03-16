"""
Universe construction — decides which tickers are eligible at each point in time.

The universe is the set of instruments the strategy is allowed to trade.
Getting this wrong is one of the most common sources of backtest inflation.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def get_universe(df: pd.DataFrame, as_of: pd.Timestamp | None = None) -> list[str]:
    """
    Return the list of tradeable tickers as of `as_of`.

    Parameters
    ----------
    df : DataFrame with MultiIndex (date, ticker)
    as_of : The evaluation date. If None, defaults to the last date in df.
    """
    all_dates = df.index.get_level_values("date")

    last_date = all_dates.max()

    try:
        snapshot = df.loc[last_date]
    except KeyError:
        logger.warning("No data for date %s, returning empty universe", last_date)
        return []

    tickers = list(snapshot.index.get_level_values("ticker").unique())
    logger.debug("Universe as of %s: %s", last_date, tickers)
    return tickers
