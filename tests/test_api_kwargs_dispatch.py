"""Tests that /api/backtest routes strategy-specific kwargs correctly."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_macd_backtest_passes_macd_kwargs(client):
    """H-6: /api/backtest for macd strategy must pass fast/slow/signal kwargs."""
    with patch("main.push_job", new_callable=AsyncMock) as mock_push:
        response = client.post("/api/backtest", json={
            "strategy": "macd",
            "fast": 8,
            "slow": 21,
            "signal": 5,
        })
        assert response.status_code == 200
        assert mock_push.called
        call_args = mock_push.call_args
        # Third positional arg is kwargs dict
        job_kwargs = call_args[0][2]
        assert "fast" in job_kwargs, (
            f"macd kwargs missing 'fast'; push_job call: {call_args}"
        )
        assert job_kwargs["fast"] == 8, (
            f"macd 'fast' should be 8; got {job_kwargs['fast']}"
        )
        assert "short_window" not in job_kwargs, (
            f"sma-specific 'short_window' should not be in macd kwargs: {job_kwargs}"
        )
        assert "long_window" not in job_kwargs, (
            f"sma-specific 'long_window' should not be in macd kwargs: {job_kwargs}"
        )


def test_rsi_backtest_passes_rsi_kwargs(client):
    """H-6: /api/backtest for rsi strategy must pass window/oversold/overbought kwargs."""
    with patch("main.push_job", new_callable=AsyncMock) as mock_push:
        response = client.post("/api/backtest", json={
            "strategy": "rsi",
            "window": 14,
            "oversold": 30,
            "overbought": 70,
        })
        assert response.status_code == 200
        assert mock_push.called
        call_args = mock_push.call_args
        job_kwargs = call_args[0][2]
        assert "window" in job_kwargs, (
            f"rsi kwargs missing 'window'; push_job call: {call_args}"
        )
        assert job_kwargs["window"] == 14, (
            f"rsi 'window' should be 14; got {job_kwargs['window']}"
        )
        assert "short_window" not in job_kwargs, (
            f"sma-specific 'short_window' should not be in rsi kwargs: {job_kwargs}"
        )


def test_sma_backtest_passes_sma_kwargs(client):
    """H-6: /api/backtest for sma_cross strategy must pass short_window/long_window kwargs."""
    with patch("main.push_job", new_callable=AsyncMock) as mock_push:
        response = client.post("/api/backtest", json={
            "strategy": "sma_cross",
            "short_window": 10,
            "long_window": 40,
        })
        assert response.status_code == 200
        assert mock_push.called
        call_args = mock_push.call_args
        job_kwargs = call_args[0][2]
        assert "short_window" in job_kwargs, (
            f"sma_cross kwargs missing 'short_window'; got: {job_kwargs}"
        )
        assert job_kwargs["short_window"] == 10
        assert job_kwargs["long_window"] == 40
