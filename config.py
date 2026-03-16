"""Pipeline configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Data ──────────────────────────────────────────────────────────────
    DATA_PATH: str = "data/sample_data.csv"

    # ── Strategy defaults ─────────────────────────────────────────────────
    SMA_SHORT_WINDOW: int = 20
    SMA_LONG_WINDOW: int = 50
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    RSI_WINDOW: int = 14
    RSI_OVERSOLD: float = 30.0
    RSI_OVERBOUGHT: float = 70.0

    # ── Risk / sizing ─────────────────────────────────────────────────────
    TRANSACTION_COST_BPS: float = 5.0   # one-way, in basis points
    MAX_POSITION_SIZE: float = 1.0      # fraction of portfolio

    # ── Calendar ──────────────────────────────────────────────────────────
    TRADING_DAYS_PER_YEAR: int = 252    # used for annualisation

    # ── Infrastructure ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── Misc ──────────────────────────────────────────────────────────────
    RISK_FREE_RATE_ANNUAL: float = 0.04  # 4 % annual


settings = Settings()
