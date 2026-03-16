"""
SSE progress manager.

Tracks pipeline execution state and streams it to connected clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Per-run state: {run_id: {"step": str, "pct": int, "ticker": str}}
_state: dict[str, dict] = {}

_cursor: str = ""


async def emit(run_id: str, step: str, pct: int, ticker: str = "") -> None:
    """Update state and advance the shared SSE cursor."""
    global _cursor
    _state[run_id] = {"step": step, "pct": pct, "ticker": ticker}
    payload = {"run_id": run_id, "step": step, "pct": pct, "ticker": ticker}
    _cursor = f"data: {json.dumps(payload)}\n\n"
    await asyncio.sleep(0)  # yield to event loop


async def stream(run_id: str, poll_interval: float = 0.3) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted events until the run reaches 100 % or times out."""
    last_pct = -1
    elapsed = 0.0
    timeout = 180.0

    while elapsed < timeout:
        state = _state.get(run_id, {"step": "pending", "pct": 0, "ticker": ""})

        if state["pct"] != last_pct:
            last_pct = state["pct"]
            yield _cursor

        if state["pct"] >= 100:
            break

        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    done = json.dumps({"run_id": run_id, "step": "done", "pct": 100})
    yield f"data: {done}\n\n"
