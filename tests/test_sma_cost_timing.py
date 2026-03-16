"""Tests that SMA cross transaction cost is applied on the NEXT day after signal change."""
import numpy as np
import pandas as pd
import pytest
from strategy.sma_cross import SmaCross as SMACrossStrategy


def test_sma_turnover_applied_next_day():
    """M-3: Turnover cost must be applied the day AFTER the signal changes, not same day.

    Using signal.shift(1).diff().abs() instead of signal.diff().abs() ensures
    the cost is not applied look-ahead on the signal-change day itself.
    """
    # Create a price series where we know exactly when the SMA cross happens
    # Flat then rising — cross will happen at a known point
    n = 60
    prices = pd.Series(
        [100.0] * 30 + [i * 2.0 + 100.0 for i in range(1, 31)],
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    df = pd.DataFrame({
        "open": prices * 0.999,
        "high": prices * 1.001,
        "low": prices * 0.998,
        "close": prices,
        "volume": 1_000_000,
        "daily_return": prices.pct_change().fillna(0),
    })

    strat = SMACrossStrategy(short_window=5, long_window=10)
    result = strat.compute(df)

    # Find days where signal changes
    signal_changes = result["signal"].diff().abs().fillna(0)
    turnover = result["turnover"].fillna(0)

    change_days = signal_changes[signal_changes > 0].index

    for day in change_days:
        # On the day the signal changes, turnover should be 0 (cost not yet applied)
        assert turnover[day] == 0.0, (
            f"Turnover applied on signal-change day {day} — should be next day"
        )
        # The day AFTER the signal change, turnover should be > 0
        next_days = result.index[result.index > day]
        if len(next_days) > 0:
            next_day = next_days[0]
            assert turnover[next_day] > 0.0, (
                f"Turnover not applied on day after signal change {next_day}"
            )
