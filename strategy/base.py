"""Abstract base class for all strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseStrategy(ABC):
    """
    A strategy receives a price DataFrame for a single ticker and produces
    a 'strategy_return' column — the daily P&L of following the strategy.

    Subclasses must implement `compute`.
    """

    name: str = "base"

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Parameters
        ----------
        df : DataFrame with columns [open, high, low, close, volume, daily_return],
             indexed by date (single ticker).

        Returns
        -------
        DataFrame with the same index plus at minimum:
            signal          : int (1 = long, 0 = flat, -1 = short)
            strategy_return : float (daily P&L fraction)
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
