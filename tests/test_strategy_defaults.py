"""Tests that strategy default parameters match config values."""
import pytest
from config import settings
from strategy.macd import Macd


def test_macd_signal_default_matches_config():
    """H-1: Macd signal default must equal MACD_SIGNAL from config, not MACD_SLOW."""
    # Instantiate with only fast/slow — signal should default to MACD_SIGNAL (9), not MACD_SLOW (26)
    strat = Macd(fast=settings.MACD_FAST, slow=settings.MACD_SLOW)
    assert strat.signal_period == settings.MACD_SIGNAL, (
        f"Expected signal_period={settings.MACD_SIGNAL} (MACD_SIGNAL) "
        f"but got {strat.signal_period} — likely defaulting to MACD_SLOW={settings.MACD_SLOW}"
    )
