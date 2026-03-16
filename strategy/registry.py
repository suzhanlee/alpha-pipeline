"""Strategy registry — maps strategy name strings to classes."""

from __future__ import annotations

from .base import BaseStrategy
from .sma_cross import SmaCross
from .macd import Macd
from .rsi import Rsi

_REGISTRY: dict[str, type[BaseStrategy]] = {
    SmaCross.name: SmaCross,
    Macd.name: Macd,
    Rsi.name: Rsi,
}

_instance_cache: dict[str, BaseStrategy] = {}


def list_strategies() -> list[str]:
    return sorted(_REGISTRY.keys())


def get_strategy(name: str, **kwargs: object) -> BaseStrategy:
    if name not in _REGISTRY:
        raise ValueError(f"Unknown strategy '{name}'. Available: {list_strategies()}")
    if name not in _instance_cache:
        _instance_cache[name] = _REGISTRY[name](**kwargs)
    return _instance_cache[name]
