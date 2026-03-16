"""Tests that /api/compare passes strategy-specific kwargs (no bleed)."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_compare_sma_kwargs_dont_bleed_into_macd(client):
    """H-7: /api/compare must not pass sma-specific params to macd strategy."""
    captured_calls = []

    async def mock_run_backtest(run_id, strategy_name, kwargs, data_path=None):
        captured_calls.append((strategy_name, dict(kwargs)))
        return {
            "run_id": run_id, "strategy": strategy_name,
            "sharpe_ratio": 1.0, "cagr": 0.1,
            "max_drawdown": -0.1, "win_rate": 0.6, "total_return": 0.1,
            "volatility_annual": 0.2, "num_days": 252,
        }

    with patch("runner.dispatcher.run_backtest", side_effect=mock_run_backtest):
        response = client.post("/api/compare", json={
            "strategies": ["sma_cross", "macd"],
            "short_window": 10,
            "long_window": 30,
        })
        assert response.status_code == 200, f"Response error: {response.text}"
        assert len(captured_calls) == 2, f"Expected 2 calls, got {len(captured_calls)}"

        for strategy_name, kwargs in captured_calls:
            if strategy_name == "macd":
                assert "short_window" not in kwargs, (
                    f"sma-specific 'short_window' bled into macd kwargs: {kwargs}"
                )
                assert "long_window" not in kwargs, (
                    f"sma-specific 'long_window' bled into macd kwargs: {kwargs}"
                )


def test_compare_macd_kwargs_dont_bleed_into_sma(client):
    """H-7: /api/compare must not pass macd-specific params to sma_cross strategy."""
    captured_calls = []

    async def mock_run_backtest(run_id, strategy_name, kwargs, data_path=None):
        captured_calls.append((strategy_name, dict(kwargs)))
        return {
            "run_id": run_id, "strategy": strategy_name,
            "sharpe_ratio": 1.0, "cagr": 0.1,
            "max_drawdown": -0.1, "win_rate": 0.6, "total_return": 0.1,
            "volatility_annual": 0.2, "num_days": 252,
        }

    with patch("runner.dispatcher.run_backtest", side_effect=mock_run_backtest):
        response = client.post("/api/compare", json={
            "strategies": ["sma_cross", "macd"],
            "short_window": 10,
            "long_window": 30,
            "fast": 8,
            "slow": 21,
            "signal": 5,
        })
        assert response.status_code == 200, f"Response error: {response.text}"

        for strategy_name, kwargs in captured_calls:
            if strategy_name == "sma_cross":
                assert "fast" not in kwargs, (
                    f"macd-specific 'fast' bled into sma_cross kwargs: {kwargs}"
                )
                assert "slow" not in kwargs, (
                    f"macd-specific 'slow' bled into sma_cross kwargs: {kwargs}"
                )
