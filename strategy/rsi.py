"""
RSI (Relative Strength Index) mean-reversion strategy.

Buy when RSI < oversold threshold, sell when RSI > overbought threshold.

STATUS: Work in progress — signal generation is implemented but
        position sizing and exit logic are incomplete.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import settings
from .base import BaseStrategy


def _compute_rsi(series: pd.Series, window: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(com=window - 1, min_periods=window).mean()
    avg_loss = loss.ewm(com=window - 1, min_periods=window).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


class Rsi(BaseStrategy):
    name = "rsi"

    def __init__(
        self,
        window: int = settings.RSI_WINDOW,
        oversold: float = settings.RSI_OVERSOLD,
        overbought: float = settings.RSI_OVERBOUGHT,
    ) -> None:
        self.window = window
        self.oversold = oversold
        self.overbought = overbought

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df["rsi"] = _compute_rsi(df["close"], self.window)

        # Entry signals
        df["signal_entry_long"] = (df["rsi"] < self.oversold).astype(int)
        df["signal_entry_short"] = (df["rsi"] > self.overbought).astype(int)

        # TODO: implement stateful position tracking
        # Currently emits entry signals but doesn't hold position until exit.
        # Placeholder: treat each day independently (incorrect for mean-reversion).
        df["signal"] = df["signal_entry_long"] - df["signal_entry_short"]

        df["turnover"] = df["signal"].diff().abs().fillna(0)
        cost_per_day = df["turnover"] * (settings.TRANSACTION_COST_BPS / 10_000)

        df["strategy_return"] = df["signal"].shift(1) * df["daily_return"] - cost_per_day

        return df.dropna(subset=["strategy_return"])
