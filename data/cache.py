"""
In-process data cache.

Avoids reloading the price CSV on every backtest request.
Intended to be replaced with a shared cache (e.g. Redis) in production.
"""

from __future__ import annotations

import pandas as pd

_cache: dict[str, pd.DataFrame] = {}


def get_cached(path: str) -> pd.DataFrame | None:
    """Return cached DataFrame for path, or None if not cached."""
    return _cache.get(str(path))


def set_cached(path: str, df: pd.DataFrame) -> None:
    """Store DataFrame in cache."""
    _cache[str(path)] = df
