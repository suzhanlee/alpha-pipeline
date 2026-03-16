"""H-3: Tests that concurrent backtests don't share _ticker_returns state."""


def test_no_global_ticker_returns():
    """H-3: _ticker_returns must NOT be a module-level global in backtest.py."""
    import runner.backtest as bt

    assert not hasattr(bt, '_ticker_returns'), (
        "_ticker_returns is a module-level global in backtest.py — "
        "concurrent runs will overwrite each other's data. "
        "Move it inside run_backtest() as a local variable."
    )
