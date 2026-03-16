"""
Simple Moving Average Crossover strategy.

Long when short SMA > long SMA, flat otherwise.
"""

from __future__ import annotations

import pandas as pd

from config import settings
from .base import BaseStrategy


class SmaCross(BaseStrategy):
    name = "sma_cross"

    def __init__(
        self,
        short_window: int = settings.SMA_SHORT_WINDOW,
        long_window: int = settings.SMA_LONG_WINDOW,
    ) -> None:
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        self.short_window = short_window
        self.long_window = long_window

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df["sma_short"] = df["close"].rolling(self.short_window, min_periods=self.short_window).mean()
        df["sma_long"] = df["close"].rolling(self.long_window, min_periods=self.long_window).mean()

        # Crossover signal: 1 when short SMA is above long SMA
        df["signal"] = (df["sma_short"] > df["sma_long"]).astype(int)

        # Transaction cost: apply on the day AFTER signal changes (no lookahead bias)
        df["turnover"] = df["signal"].shift(1).diff().abs().fillna(0)
        cost_per_day = df["turnover"] * (settings.TRANSACTION_COST_BPS / 10_000)

        df["strategy_return"] = df["signal"] * df["daily_return"] - cost_per_day

        return df.dropna(subset=["strategy_return"])
