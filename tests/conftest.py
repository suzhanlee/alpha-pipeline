"""Shared test fixtures."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def flat_returns() -> pd.Series:
    """252 days of constant +0.1 % daily return."""
    rng = np.random.default_rng(0)
    base = pd.Series([0.001] * 252, name="returns")
    noise = pd.Series(rng.normal(0, 0.0001, 252))
    return base + noise


@pytest.fixture()
def sample_price_df() -> pd.DataFrame:
    """Minimal multi-ticker OHLCV DataFrame for unit tests."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2022-01-03", periods=300, freq="B")
    tickers = ["ALPHA", "BETA", "GAMMA"]

    rows = []
    for ticker in tickers:
        price = 100.0
        # GAMMA: data ends after 150 days (simulates delisting)
        n = 150 if ticker == "GAMMA" else 300
        for date in dates[:n]:
            ret = rng.normal(0.0003, 0.012)
            close = round(price * (1 + ret), 4)
            rows.append({
                "date": date,
                "ticker": ticker,
                "open": round(price * (1 + rng.normal(0, 0.002)), 4),
                "high": round(max(price, close) * (1 + abs(rng.normal(0, 0.003))), 4),
                "low": round(min(price, close) * (1 - abs(rng.normal(0, 0.003))), 4),
                "close": close,
                "volume": int(rng.integers(500_000, 2_000_000)),
            })
            price = close

    df = pd.DataFrame(rows)
    df["daily_return"] = df.groupby("ticker")["close"].pct_change()
    df = df.set_index(["date", "ticker"]).sort_index()
    return df
