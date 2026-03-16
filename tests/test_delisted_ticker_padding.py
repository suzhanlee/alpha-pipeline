"""H-4: Tests that delisted ticker NaN values are not padded with zeros."""
import pandas as pd


def test_portfolio_return_excludes_nan_not_zero():
    """H-4: NaN returns from delisted tickers must be excluded (not filled with 0).

    .fillna(0) pads delisted periods with zero, which deflates portfolio returns.
    Instead, pd.concat + mean() naturally excludes NaN via skipna=True.
    """
    active_returns = pd.Series([0.01, 0.01, 0.01, 0.01, 0.01], name="ACTIVE")
    delisted_returns = pd.Series([0.01, 0.01, 0.01, None, None], name="DELISTED")

    # fillna(0) approach (buggy):
    df_with_zeros = pd.DataFrame({
        "ACTIVE": active_returns,
        "DELISTED": delisted_returns.fillna(0),
    })
    buggy_portfolio = df_with_zeros.mean(axis=1)

    # NaN-aware approach (correct):
    df_without_zeros = pd.DataFrame({
        "ACTIVE": active_returns,
        "DELISTED": delisted_returns,
    })
    correct_portfolio = df_without_zeros.mean(axis=1)

    assert buggy_portfolio.iloc[3] < correct_portfolio.iloc[3], (
        "fillna(0) should dilute returns when ticker is delisted"
    )
    assert abs(correct_portfolio.iloc[3] - 0.01) < 1e-6, (
        f"After delisting, portfolio return should equal ACTIVE (0.01), got {correct_portfolio.iloc[3]}"
    )
    assert abs(buggy_portfolio.iloc[3] - 0.005) < 1e-6, (
        f"fillna(0) should give 0.005, got {buggy_portfolio.iloc[3]}"
    )


def test_backtest_does_not_use_fillna_on_portfolio():
    """H-4: run_backtest must not call .fillna(0) before portfolio mean."""
    import inspect
    from runner import backtest

    source = inspect.getsource(backtest.run_backtest)
    assert "fillna(0)" not in source, (
        "run_backtest still contains .fillna(0) on portfolio returns — "
        "this deflates returns when tickers are delisted"
    )
