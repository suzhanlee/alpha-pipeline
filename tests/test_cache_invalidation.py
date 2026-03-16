"""Tests that the data cache invalidates when the file is modified."""
import os
import time
import tempfile
import pandas as pd
import pytest
from data.cache import get_cached, set_cached


def test_cache_invalidates_on_file_modification(tmp_path):
    """H-5: Cache must return None if the file has been modified since caching."""
    # Create a temp CSV file
    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text("date,close\n2020-01-01,100\n")
    path = str(csv_file)

    # Create a dummy DataFrame and cache it
    df = pd.DataFrame({"close": [100]}, index=pd.to_datetime(["2020-01-01"]))
    set_cached(path, df)

    # Verify it's cached
    assert get_cached(path) is not None

    # Wait a moment then modify the file (ensure mtime changes)
    time.sleep(0.05)
    csv_file.write_text("date,close\n2020-01-01,200\n2020-01-02,201\n")

    # Cache should be invalidated
    result = get_cached(path)
    assert result is None, "Cache should return None after file modification"
