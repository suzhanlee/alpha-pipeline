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
    short_window: int = Field(default=20, ge=2)
    long_window: int = Field(default=50, ge=3)


class BacktestStarted(BaseModel):
    run_id: str
    strategy: str
    status: str = "queued"


class CompareRequest(BaseModel):
    strategies: list[str] = Field(default=["sma_cross", "macd"])
    short_window: int = Field(default=20, ge=2)
    long_window: int = Field(default=50, ge=3)


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

    kwargs = {"short_window": req.short_window, "long_window": req.long_window}
    result = await run_comparison(req.strategies, kwargs, "data/sample_data.csv")
    result["multiple_testing_adjusted"] = False
    return result
