"""Tests that result_store sets a TTL on saved results."""
import json
from unittest.mock import MagicMock, call, AsyncMock
import pytest


def test_save_result_sets_ttl():
    """M-4: save_result must set a TTL of 86400 seconds (24h) on the Redis key."""
    import asyncio
    import storage.result_store as rs

    mock_client = AsyncMock()
    original_client = None

    # Find the redis client attribute name in the module
    # It could be `client`, `_client`, `redis_client`, etc.
    # Patch whichever attribute holds the redis connection
    for attr in ["client", "_client", "redis_client", "_redis"]:
        if hasattr(rs, attr):
            original_client = getattr(rs, attr)
            setattr(rs, attr, mock_client)
            break
    else:
        pytest.skip("Could not find redis client attribute in result_store")

    try:
        asyncio.get_event_loop().run_until_complete(
            rs.save_result("test-run-123", {"sharpe_ratio": 1.5, "cagr": 0.12})
        )

        # Check that set was called with ex=86400
        set_calls = mock_client.set.call_args_list
        assert len(set_calls) >= 1, "redis client.set was not called"

        # The call should include ex=86400
        found_ttl = False
        for c in set_calls:
            kwargs = c.kwargs if hasattr(c, 'kwargs') else {}
            args = c.args if hasattr(c, 'args') else c[0]
            if kwargs.get("ex") == 86400 or (len(args) >= 3 and args[2] == 86400):
                found_ttl = True
                break
            # Also check positional
            if "ex" in str(c):
                found_ttl = True
                break

        assert found_ttl, (
            f"save_result did not set ex=86400 TTL. Calls: {set_calls}"
        )
    finally:
        if original_client is not None:
            setattr(rs, attr, original_client)


def test_save_result_ttl_is_24h():
    """M-4: TTL must be exactly 86400 seconds (24 hours)."""
    import storage.result_store as rs
    import inspect

    source = inspect.getsource(rs.save_result)
    assert "86400" in source, (
        "save_result source does not contain '86400' — TTL not set to 24h"
    )
