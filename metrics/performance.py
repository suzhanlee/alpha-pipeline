"""
Performance metrics for backtested strategies.

All metrics assume daily return series as input.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.04) -> float:
    """
    Annualised Sharpe ratio.

    Parameters
    ----------
    returns : daily strategy returns (not cumulative)
    risk_free_rate : annual risk-free rate (default 4 %)
    """
    # Convert annual risk-free rate to daily
    daily_rf = risk_free_rate / 252
    excess = returns - daily_rf

    if excess.std() < 1e-10:
        return 0.0

    return float(excess.mean() / excess.std())


def max_drawdown(returns: pd.Series) -> float:
    """Maximum peak-to-trough drawdown (negative number)."""
    cumulative = (1 + returns).cumprod()
    rolling_peak = cumulative.cummax()
    drawdown = (cumulative - rolling_peak) / rolling_peak
    return float(drawdown.min())


def cagr(returns: pd.Series) -> float:
    """Compound Annual Growth Rate."""
    total = float((1 + returns).prod())
    years = len(returns) / 252
    if years == 0 or total <= 0:
        return float('nan')
    return float(total ** (1 / years) - 1)


def win_rate(returns: pd.Series) -> float:
    """Fraction of trading days with positive return."""
    active = returns[returns != 0]
    if len(active) == 0:
        return 0.0
    return float((active > 0).mean())


def compute_metrics(returns: pd.Series, risk_free_rate: float = 0.04) -> dict:
    """Compute all standard performance metrics.

    win_rate: Zero-return days (no position) are excluded from the denominator.
    Only active trading days (non-zero returns) are counted.
    """
    cagr_val = cagr(returns)
    return {
        "sharpe_ratio": round(sharpe_ratio(returns, risk_free_rate), 4),
        "cagr": float('nan') if (isinstance(cagr_val, float) and cagr_val != cagr_val) else round(cagr_val, 4),
        "max_drawdown": round(max_drawdown(returns), 4),
        "win_rate": round(win_rate(returns), 4),
        "total_return": round(float((1 + returns).prod() - 1), 4),
        "volatility_annual": round(float(returns.std() * np.sqrt(252)), 4),
        "num_days": len(returns),
    }
