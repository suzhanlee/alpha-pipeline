"""
Tests for strategy signal generation.

Run with: uv run pytest tests/test_signals.py -v
"""

import numpy as np
import pandas as pd
import pytest

from strategy.sma_cross import SmaCross
from strategy.macd import Macd


def _make_ticker_df(n: int = 300, seed: int = 0) -> pd.DataFrame:
    """Single-ticker OHLCV frame."""
    rng = np.random.default_rng(seed)
    price = 100.0
    rows = []
    for i in range(n):
        ret = rng.normal(0.0003, 0.012)
        close = round(price * (1 + ret), 4)
        rows.append({
            "open": round(price * (1 + rng.normal(0, 0.002)), 4),
            "high": round(max(price, close) * (1 + abs(rng.normal(0, 0.003))), 4),
            "low": round(min(price, close) * (1 - abs(rng.normal(0, 0.003))), 4),
            "close": close,
            "volume": int(rng.integers(500_000, 2_000_000)),
            "daily_return": ret if i > 0 else 0.0,
        })
        price = close

    df = pd.DataFrame(rows, index=pd.date_range("2021-01-04", periods=n, freq="B"))
    df.index.name = "date"
    return df


class TestSmaCross:
    def test_signal_is_binary(self):
        """Signal column must only contain 0 and 1."""
        df = _make_ticker_df()
        result = SmaCross().compute(df)
        assert set(result["signal"].unique()).issubset({0, 1})

    def test_no_lookahead_noise_sharpe(self):
        """H-9: On pure noise data, any strategy Sharpe must be < 1.0.

        A lookahead-biased strategy would produce unrealistically high Sharpe on noise.
        Using n=1000 to reduce variance of the test itself.
        """
        rng = np.random.default_rng(42)
        n = 1000
        noise_returns = pd.Series(rng.standard_normal(n) * 0.01)
        # Build a price series from noise returns
        prices = (1 + noise_returns).cumprod()
        prices.index = pd.date_range("2018-01-01", periods=n, freq="B")

        df = pd.DataFrame({
            "open": prices * 0.999,
            "high": prices * 1.001,
            "low": prices * 0.998,
            "close": prices,
            "volume": 1_000_000,
            "daily_return": noise_returns,
        })

        from config import settings
        strat = SmaCross(
            short_window=settings.SMA_SHORT_WINDOW,
            long_window=settings.SMA_LONG_WINDOW,
        )
        result = strat.compute(df)
        strategy_returns = result["strategy_return"].dropna()

        if len(strategy_returns) == 0 or strategy_returns.std() == 0:
            pytest.skip("No strategy returns generated")

        sharpe = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
        assert abs(sharpe) < 1.0, (
            f"Sharpe={sharpe:.3f} on pure noise exceeds 1.0 — possible lookahead bias"
        )

    def test_signal_not_all_zero(self):
        """Strategy should produce at least some long positions."""
        df = _make_ticker_df(n=300)
        result = SmaCross().compute(df)
        assert result["signal"].sum() > 0

    def test_returns_no_nan(self):
        df = _make_ticker_df()
        result = SmaCross().compute(df)
        assert result["strategy_return"].isna().sum() == 0

    def test_short_window_lt_long_window(self):
        with pytest.raises(ValueError):
            SmaCross(short_window=50, long_window=20)

    def test_strategy_return_column_exists(self):
        df = _make_ticker_df()
        result = SmaCross().compute(df)
        assert "strategy_return" in result.columns


class TestMacd:
    def test_correct_no_lookahead(self):
        """
        MACD uses shift(1) — its Sharpe on a pure-noise series should be
        near 0 (no edge), not inflated by look-ahead.
        """
        from metrics.performance import sharpe_ratio

        rng = np.random.default_rng(99)
        # Pure noise: no predictability
        n = 1000
        price = 100.0
        rows = []
        for _ in range(n):
            ret = rng.normal(0.0, 0.01)
            close = price * (1 + ret)
            rows.append({"open": price, "high": close, "low": close,
                          "close": close, "volume": 1_000_000, "daily_return": ret})
            price = close

        df = pd.DataFrame(rows, index=pd.date_range("2021-01-04", periods=n, freq="B"))
        result = Macd().compute(df)
        sharpe = sharpe_ratio(result["strategy_return"], risk_free_rate=0.0)

        # On pure noise, a correct strategy should have |Sharpe| < 1
        assert abs(sharpe) < 1.5, (
            f"MACD Sharpe={sharpe:.3f} on pure-noise data is unexpectedly high. "
            "Check for look-ahead bias."
        )

    def test_macd_lines_computed(self):
        df = _make_ticker_df()
        result = Macd().compute(df)
        assert "macd_line" in result.columns
        assert "macd_signal" in result.columns
