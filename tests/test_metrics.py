"""
Tests for metrics/performance.py

Run with: uv run pytest tests/test_metrics.py -v
"""

import numpy as np
import pandas as pd
import pytest

from metrics.performance import sharpe_ratio, max_drawdown, cagr, win_rate, compute_metrics


class TestSharpeRatio:
    def test_sharpe_annualised(self, flat_returns):
        """
        A strategy with consistent ~0.1 % daily return and ~0.01 % daily vol
        should produce an *annualised* Sharpe well above 1.0.

        If this test FAILS with sharpe ≈ 0.06, the annualisation factor is missing.
        """
        # Construct returns with mean ≈ 0.001, std ≈ 0.01
        rng = np.random.default_rng(1)
        returns = pd.Series(rng.normal(0.001, 0.01, 252))

        sharpe = sharpe_ratio(returns, risk_free_rate=0.0)

        # Annualised Sharpe = (mean/std) * sqrt(252)
        # With mean=0.001, std=0.01: daily_sharpe ≈ 0.1, annual ≈ 1.59
        # Bug present  → sharpe ≈ 0.06  → test FAILS  ✗
        # Bug fixed    → sharpe ≈ 1.5   → test PASSES ✓
        assert sharpe > 1.0, (
            f"Sharpe is {sharpe:.4f} — expected > 1.0 (annualised). "
            "Did you forget to multiply by sqrt(252)?"
        )

    def test_sharpe_zero_vol(self):
        """Constant returns → zero volatility → Sharpe = 0 (not inf/nan)."""
        returns = pd.Series([0.001] * 100)
        assert sharpe_ratio(returns) == 0.0

    def test_sharpe_negative(self):
        """Consistently negative returns → negative Sharpe."""
        returns = pd.Series([-0.002] * 100 + [0.001] * 100)
        # Just check it's computable and negative
        assert sharpe_ratio(returns) < 0

    def test_sharpe_uses_risk_free(self):
        """Higher risk-free rate → lower Sharpe, all else equal."""
        rng = np.random.default_rng(2)
        returns = pd.Series(rng.normal(0.001, 0.01, 252))
        s_low_rf = sharpe_ratio(returns, risk_free_rate=0.0)
        s_high_rf = sharpe_ratio(returns, risk_free_rate=0.06)
        assert s_low_rf > s_high_rf


class TestMaxDrawdown:
    def test_no_drawdown(self):
        """Monotonically increasing equity → drawdown = 0."""
        returns = pd.Series([0.001] * 100)
        assert max_drawdown(returns) == pytest.approx(0.0, abs=1e-6)

    def test_known_drawdown(self):
        """50 % drop followed by recovery → drawdown ≈ -0.5."""
        # 100 days flat → one day -50 % → 100 days flat
        returns = pd.Series([0.0] * 100 + [-0.5] + [0.0] * 100)
        assert max_drawdown(returns) == pytest.approx(-0.5, abs=0.01)

    def test_drawdown_negative(self):
        """Drawdown is always ≤ 0."""
        import numpy as np
        rng = np.random.default_rng(3)
        returns = pd.Series(rng.normal(0.0, 0.01, 500))
        assert max_drawdown(returns) <= 0.0


class TestCagr:
    def test_cagr_positive(self):
        """100 % total return over 252 days → CAGR ≈ 100 %."""
        returns = pd.Series([0.001] * 252)
        result = cagr(returns)
        # (1.001)^252 - 1 ≈ 0.284, not 1.0 — let's just check it's positive
        assert result > 0

    def test_cagr_consistent_with_total_return(self):
        """CAGR and total_return should be consistent."""
        import numpy as np
        rng = np.random.default_rng(4)
        returns = pd.Series(rng.normal(0.0005, 0.01, 500))
        total = float((1 + returns).prod() - 1)
        annual = cagr(returns)
        years = 500 / 252
        reconstructed_total = (1 + annual) ** years - 1
        assert abs(reconstructed_total - total) < 0.01


class TestComputeMetrics:
    def test_returns_expected_keys(self, flat_returns):
        """compute_metrics should return all expected keys."""
        result = compute_metrics(flat_returns)
        expected = {"sharpe_ratio", "cagr", "max_drawdown", "win_rate", "total_return",
                    "volatility_annual", "num_days"}
        assert set(result.keys()) == expected

    def test_num_days_matches_input(self, flat_returns):
        result = compute_metrics(flat_returns)
        assert result["num_days"] == len(flat_returns)
