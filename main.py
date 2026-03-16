"""
Alpha Pipeline Recovery — API service.

This process handles HTTP only. Backtest execution runs in the worker service.
Job dispatch goes through Redis. Results are read from Redis.

Endpoints
---------
GET  /                           Health check
GET  /strategies                 List available strategies
POST /api/backtest               Enqueue a backtest job
GET  /api/progress/{run_id}      SSE stream of run progress
GET  /api/result/{run_id}        Fetch final result (once complete)
POST /api/compare                Run multiple strategies and compare
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from mq.redis_queue import push_job
from runner.dispatcher import run_comparison
from runner.progress import stream
from storage.result_store import get_result
from strategy import list_strategies


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Alpha Pipeline Recovery",
    description="Arkraft mini alpha research pipeline — find the bugs.",
    lifespan=lifespan,
)


# ── Request / Response models ──────────────────────────────────────────────────

class BacktestRequest(BaseModel):
    strategy: str = Field(default="sma_cross", description="Strategy name")
    # SMA Cross params
    short_window: int = Field(default=20, ge=2)
    long_window: int = Field(default=50, ge=3)
    # MACD params
    fast: int | None = Field(default=None, ge=1)
    slow: int | None = Field(default=None, ge=1)
    signal: int | None = Field(default=None, ge=1)
    # RSI params
    window: int | None = Field(default=None, ge=1)
    oversold: float | None = Field(default=None)
    overbought: float | None = Field(default=None)


class BacktestStarted(BaseModel):
    run_id: str
    strategy: str
    status: str = "queued"


class CompareRequest(BaseModel):
    strategies: list[str] = Field(default=["sma_cross", "macd"])
    # SMA Cross params
    short_window: int = Field(default=20, ge=2)
    long_window: int = Field(default=50, ge=3)
    # MACD params
    fast: int | None = Field(default=None, ge=1)
    slow: int | None = Field(default=None, ge=1)
    signal: int | None = Field(default=None, ge=1)
    # RSI params
    window: int | None = Field(default=None, ge=1)
    oversold: float | None = Field(default=None)
    overbought: float | None = Field(default=None)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/")
async def health() -> dict:
    return {"status": "ok", "strategies": list_strategies()}


@app.get("/strategies")
async def strategies() -> dict:
    return {"strategies": list_strategies()}


@app.post("/api/backtest", response_model=BacktestStarted)
async def start_backtest(req: BacktestRequest) -> BacktestStarted:
    available = list_strategies()
    if req.strategy not in available:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown strategy '{req.strategy}'. Available: {available}",
        )

    run_id = str(uuid.uuid4())

    kwargs: dict = {}
    if req.strategy == "sma_cross":
        kwargs = {"short_window": req.short_window, "long_window": req.long_window}
    elif req.strategy == "macd":
        kwargs = {k: v for k, v in {"fast": req.fast, "slow": req.slow, "signal": req.signal}.items() if v is not None}
    elif req.strategy == "rsi":
        kwargs = {k: v for k, v in {"window": req.window, "oversold": req.oversold, "overbought": req.overbought}.items() if v is not None}

    await push_job(run_id, req.strategy, kwargs)

    return BacktestStarted(run_id=run_id, strategy=req.strategy)


@app.get("/api/progress/{run_id}")
async def progress(run_id: str) -> StreamingResponse:
    return StreamingResponse(
        stream(run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/result/{run_id}")
async def result(run_id: str) -> dict:
    data = await get_result(run_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Run not found or still in progress.")
    return data


@app.post("/api/compare")
async def compare(req: CompareRequest) -> dict:
    available = list_strategies()
    unknown = [s for s in req.strategies if s not in available]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown strategies: {unknown}. Available: {available}",
        )

    _SMA_KEYS = {"short_window", "long_window"}
    _MACD_KEYS = {"fast", "slow", "signal"}
    _RSI_KEYS = {"window", "oversold", "overbought"}
    _STRATEGY_KEYS: dict[str, set] = {
        "sma_cross": _SMA_KEYS,
        "macd": _MACD_KEYS,
        "rsi": _RSI_KEYS,
    }

    _optional = {
        "fast": req.fast, "slow": req.slow, "signal": req.signal,
        "window": req.window, "oversold": req.oversold, "overbought": req.overbought,
    }
    _all_kwargs: dict = {
        "short_window": req.short_window,
        "long_window": req.long_window,
        **{k: v for k, v in _optional.items() if v is not None},
    }

    per_strategy_kwargs = {
        strategy: {k: v for k, v in _all_kwargs.items() if k in _STRATEGY_KEYS.get(strategy, set())}
        for strategy in req.strategies
    }

    return await run_comparison(req.strategies, per_strategy_kwargs, "data/sample_data.csv")
