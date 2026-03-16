"""
Price data loading and validation.

Expected CSV columns: date, ticker, open, high, low, close, volume
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .cache import get_cached, set_cached

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"date", "ticker", "open", "high", "low", "close", "volume"}


def load_price_data(path: str | Path) -> pd.DataFrame:
    """
    Load OHLCV data from CSV.

    Returns a DataFrame indexed by (date, ticker) with columns:
        open, high, low, close, volume, daily_return
    """
    path = Path(path)

    cached = get_cached(str(path))
    if cached is not None:
        logger.debug("Cache hit for %s", path)
        return cached

    if not path.exists():
        raise FileNotFoundError(
            f"Data file not found: {path}\n"
            "Run `uv run python scripts/generate_data.py` first."
        )

    df = pd.read_csv(path, parse_dates=["date"])

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}")

    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    # Per-ticker daily return (close-to-close)
    df["daily_return"] = df.groupby("ticker")["close"].pct_change()

    df["daily_return"] = df["daily_return"].fillna(0)

    df = df.set_index(["date", "ticker"]).sort_index()

    n_tickers = df.index.get_level_values("ticker").nunique()
    n_dates = df.index.get_level_values("date").nunique()
    logger.info("Loaded %d tickers × %d dates from %s", n_tickers, n_dates, path)

    set_cached(str(path), df)
    return df
