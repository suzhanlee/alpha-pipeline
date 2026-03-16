"""
Generate synthetic OHLCV price data for the three-ticker universe.

    uv run python scripts/generate_data.py

Output: data/sample_data.csv
"""

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path


def _trading_days(start: date, n: int) -> list[date]:
    days, current = [], start
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _generate_ticker(
    dates: list[date],
    start_price: float,
    mu: float,
    sigma: float,
    seed: int,
) -> list[dict]:
    rng = random.Random(seed)
    rows, price = [], start_price
    for d in dates:
        daily_return = rng.gauss(mu, sigma)
        close = round(price * (1 + daily_return), 4)
        open_ = round(price * (1 + rng.gauss(0, sigma * 0.3)), 4)
        high = round(max(open_, close) * (1 + abs(rng.gauss(0, sigma * 0.4))), 4)
        low = round(min(open_, close) * (1 - abs(rng.gauss(0, sigma * 0.4))), 4)
        volume = max(int(rng.gauss(1_200_000, 300_000)), 100_000)
        rows.append({
            "date": d.isoformat(),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })
        price = close
    return rows


def main() -> None:
    out_path = Path("data/sample_data.csv")
    out_path.parent.mkdir(exist_ok=True)

    all_days = _trading_days(date(2019, 1, 2), 1300)  # ~5 years

    # GAMMA is delisted after 650 trading days (~2.5 years)
    tickers = {
        "ALPHA": (all_days,        100.0, 0.0004, 0.011, 42),
        "BETA":  (all_days,        80.0,  0.0002, 0.014, 17),
        "GAMMA": (all_days[:650],  60.0,  0.0001, 0.018, 99),
    }

    rows = []
    for ticker, (days, start, mu, sigma, seed) in tickers.items():
        for row in _generate_ticker(days, start, mu, sigma, seed):
            rows.append({"ticker": ticker, **row})

    rows.sort(key=lambda r: (r["date"], r["ticker"]))

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["date", "ticker", "open", "high", "low", "close", "volume"]
        )
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    for ticker in tickers:
        n = sum(1 for r in rows if r["ticker"] == ticker)
        print(f"  {ticker}: {n} rows")
    print(f"Generated {out_path} — {total} rows total")


if __name__ == "__main__":
    main()
