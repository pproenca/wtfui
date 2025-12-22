"""Tests for console dashboard component."""

import asyncio
import contextlib

import pytest

# Check if psutil is available
try:
    import psutil  # noqa: F401

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil required for polling tests")
async def test_dashboard_task_cleanup():
    """Verify polling task is properly tracked and can be cancelled."""
    from components.dashboard import _poll_stats
    from state import SystemState

    state = SystemState()

    # Create a task that we'll cancel
    task = asyncio.create_task(_poll_stats(state))

    # Give it time to start
    await asyncio.sleep(0.1)

    # Should be running
    assert not task.done()

    # Cancel it
    task.cancel()

    # Should cancel cleanly without error
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil required for polling tests")
async def test_poll_stats_handles_cancellation():
    """Verify _poll_stats exits cleanly when cancelled."""
    from components.dashboard import _poll_stats
    from state import SystemState

    state = SystemState()
    task = asyncio.create_task(_poll_stats(state))

    # Let it run briefly
    await asyncio.sleep(0.05)

    # Cancel
    task.cancel()

    with contextlib.suppress(asyncio.CancelledError):
        await task

    # Task should be done
    assert task.done()
