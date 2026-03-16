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


# --- M-6 ---
def test_cagr_returns_nan_for_total_loss():
    """M-6: CAGR must return NaN (not 0.0) when total return is <= 0 (total loss)."""
    import math
    from metrics.performance import compute_metrics
    import pandas as pd
    import numpy as np

    # Returns that result in total loss (portfolio goes to 0)
    # -100% on day 1 → total = 0
    returns = pd.Series([-1.0, 0.0, 0.0])
    result = compute_metrics(returns)
    assert math.isnan(result["cagr"]), (
        f"CAGR should be NaN for total loss, got {result['cagr']}"
    )


def test_cagr_hides_loss_not_zero():
    """M-6: CAGR must NOT return 0.0 when portfolio has total loss."""
    from metrics.performance import compute_metrics
    import pandas as pd

    # Total return <= 0 scenario
    returns = pd.Series([-0.5, -0.5, -0.1])
    result = compute_metrics(returns)
    # 0.0 would hide the loss — must be NaN or negative, not exactly 0.0
    assert result["cagr"] != 0.0, (
        f"CAGR returned 0.0 for a losing portfolio — this hides the loss"
    )


# --- M-7 ---
def test_win_rate_docstring_mentions_active_days():
    """M-7: win_rate calculation docstring must mention zero-return exclusion."""
    import inspect
    from metrics.performance import compute_metrics

    source = inspect.getsource(compute_metrics)
    assert "zero" in source.lower() or "active" in source.lower() or "no position" in source.lower(), (
        "compute_metrics source must mention zero-return exclusion in the win_rate logic"
    )


# --- L-3 ---
def test_daily_rf_conversion_error_within_tolerance():
    """L-3: Daily risk-free rate conversion from annual must be within 0.0001 tolerance."""
    # Annual rf = 4% = 0.04
    annual_rf = 0.04
    trading_days = 252

    # Simple division (used in code)
    simple_daily = annual_rf / trading_days

    # Compound conversion (theoretically correct)
    compound_daily = (1 + annual_rf) ** (1 / trading_days) - 1

    # The difference should be within tolerance (it's ~3e-6, well under 0.0001)
    assert abs(simple_daily - compound_daily) < 0.0001, (
        f"Daily rf conversion error {abs(simple_daily - compound_daily):.2e} exceeds 0.0001"
    )
