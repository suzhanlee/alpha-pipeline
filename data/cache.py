"""
In-process data cache.

Avoids reloading the price CSV on every backtest request.
Intended to be replaced with a shared cache (e.g. Redis) in production.
"""

from __future__ import annotations

import os

import pandas as pd

_cache: dict[str, dict] = {}  # path -> {"df": DataFrame, "mtime": float}


def get_cached(path: str) -> pd.DataFrame | None:
    """Return cached DataFrame for path, or None if not cached or file modified."""
    entry = _cache.get(str(path))
    if entry is None:
        return None
    if os.path.getmtime(str(path)) != entry["mtime"]:
        return None
    return entry["df"]


def set_cached(path: str, df: pd.DataFrame) -> None:
    """Store DataFrame in cache alongside the current file mtime."""
    _cache[str(path)] = {"df": df, "mtime": os.path.getmtime(str(path))}
