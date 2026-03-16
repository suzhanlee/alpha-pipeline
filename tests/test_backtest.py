"""
Integration tests for the backtest runner.

Run with: uv run pytest tests/test_backtest.py -v
"""

import asyncio

import pandas as pd
import pytest

from runner.backtest import run_backtest


class TestBacktestIntegration:
    @pytest.mark.asyncio
    async def test_backtest_runs(self, sample_price_df, tmp_path, monkeypatch):
        """Full pipeline runs without exceptions and returns expected keys."""
        # Patch data loading to return our fixture
        import data.loader as loader_module
        monkeypatch.setattr(loader_module, "load_price_data", lambda _: sample_price_df)

        result = await run_backtest("run-001", "sma_cross")

        assert result["run_id"] == "run-001"
        assert result["strategy"] == "sma_cross"
        assert "sharpe_ratio" in result
        assert "total_return" in result
        assert "max_drawdown" in result
        assert result["max_drawdown"] <= 0

    @pytest.mark.asyncio
    async def test_macd_backtest_runs(self, sample_price_df, monkeypatch):
        """MACD strategy runs end-to-end."""
        import data.loader as loader_module
        monkeypatch.setattr(loader_module, "load_price_data", lambda _: sample_price_df)

        result = await run_backtest("run-002", "macd")
        assert "sharpe_ratio" in result
        assert result.get("error") is None

    @pytest.mark.asyncio
    async def test_reproducibility(self, sample_price_df, monkeypatch):
        """Same inputs → identical outputs (no random state in backtest)."""
        import data.loader as loader_module
        monkeypatch.setattr(loader_module, "load_price_data", lambda _: sample_price_df)

        r1 = await run_backtest("run-rep-1", "sma_cross")
        r2 = await run_backtest("run-rep-2", "sma_cross")

        assert r1["sharpe_ratio"] == r2["sharpe_ratio"]
        assert r1["total_return"] == r2["total_return"]

    @pytest.mark.asyncio
    async def test_universe_excludes_delisted(self, sample_price_df, monkeypatch):
        """
        GAMMA is delisted halfway through — the universe builder should include it
        for dates before delisting.

        This test documents the expected (correct) behaviour: tickers present
        at a given date should appear in the universe for that date, even if
        they are later delisted.
        """
        import data.loader as loader_module
        import data.universe as universe_module
        monkeypatch.setattr(loader_module, "load_price_data", lambda _: sample_price_df)

        # The universe at an early date should include GAMMA
        early_date = pd.Timestamp("2022-04-01")
        universe = universe_module.get_universe(sample_price_df, as_of=early_date)

        assert "GAMMA" in universe, (
            "GAMMA should be in the universe at an early date (it was listed then). "
            "Looks like the universe filter has survivorship bias — "
            "it's excluding tickers that later got delisted."
        )
