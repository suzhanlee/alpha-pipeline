"""Tests that data loader validates close prices are positive."""
import os
import tempfile
import pandas as pd
import pytest


def test_loader_rejects_zero_close_price(tmp_path):
    """M-8: Loader must raise ValueError when close price is zero."""
    from data.loader import load_price_data

    # Create CSV with a zero close price
    csv_content = """date,ticker,open,high,low,close,volume
2020-01-01,AAPL,100,105,99,100,1000000
2020-01-02,AAPL,100,105,99,0,1000000
2020-01-03,AAPL,100,105,99,102,1000000
"""
    csv_file = tmp_path / "test_prices.csv"
    csv_file.write_text(csv_content)

    with pytest.raises(ValueError, match="close"):
        load_price_data(str(csv_file))


def test_loader_rejects_negative_close_price(tmp_path):
    """M-8: Loader must raise ValueError when close price is negative."""
    from data.loader import load_price_data

    csv_content = """date,ticker,open,high,low,close,volume
2020-01-01,AAPL,100,105,99,100,1000000
2020-01-02,AAPL,100,105,99,-5,1000000
"""
    csv_file = tmp_path / "test_prices.csv"
    csv_file.write_text(csv_content)

    with pytest.raises(ValueError, match="close"):
        load_price_data(str(csv_file))


def test_loader_accepts_positive_close_prices(tmp_path):
    """M-8: Loader must accept data where all close prices are positive."""
    from data.loader import load_price_data

    csv_content = """date,ticker,open,high,low,close,volume
2020-01-01,AAPL,100,105,99,100,1000000
2020-01-02,AAPL,101,106,100,103,1000000
2020-01-03,AAPL,103,108,102,107,1000000
"""
    csv_file = tmp_path / "test_prices.csv"
    csv_file.write_text(csv_content)

    # Should not raise
    df = load_price_data(str(csv_file))
    assert df is not None
