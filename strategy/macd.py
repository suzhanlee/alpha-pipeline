"""
MACD (Moving Average Convergence/Divergence) strategy.

Long when MACD line crosses above signal line, flat otherwise.
"""

from __future__ import annotations

import pandas as pd

from config import settings
from .base import BaseStrategy


class Macd(BaseStrategy):
    name = "macd"

    def __init__(
        self,
        fast: int = settings.MACD_FAST,
        slow: int = settings.MACD_SLOW,
        signal: int = settings.MACD_SIGNAL,
    ) -> None:
        self.fast = fast
        self.slow = slow
        self.signal_period = signal

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        ema_fast = df["close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.slow, adjust=False).mean()

        df["macd_line"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd_line"].ewm(span=self.signal_period, adjust=False).mean()
        df["macd_hist"] = df["macd_line"] - df["macd_signal"]

        # Signal: long when MACD line is above signal line
        df["signal"] = (df["macd_line"] > df["macd_signal"]).astype(int)

        # Correct: use previous day's signal to avoid look-ahead
        df["turnover"] = df["signal"].diff().abs().fillna(0)
        cost_per_day = df["turnover"] * (settings.TRANSACTION_COST_BPS / 10_000)

        df["strategy_return"] = df["signal"].shift(1) * df["daily_return"] - cost_per_day

        return df.dropna(subset=["strategy_return"])
