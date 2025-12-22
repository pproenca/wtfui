import asyncio
import threading
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_render_frame_runs_in_thread():
    """Verify _render_frame is offloaded to thread pool."""
    from wtfui.tui.runtime import TUIRuntime

    runtime = TUIRuntime.__new__(TUIRuntime)
    runtime.running = False
    runtime.is_dirty = True
    runtime.fps = 60
    runtime.render_lock = threading.RLock()

    # Mock renderer with proper return values
    renderer = MagicMock()
    renderer.flush.return_value = ""
    runtime.renderer = renderer

    runtime.layout_root = MagicMock()
    runtime.element_tree = MagicMock()
    runtime.needs_rebuild = False
    runtime.inline = False

    # Track if to_thread was used
    to_thread_called = False

    async def mock_to_thread(func, *args, **kwargs):
        nonlocal to_thread_called
        to_thread_called = True
        return func(*args, **kwargs)

    with patch.object(asyncio, "to_thread", mock_to_thread):
        # Run one iteration
        runtime.running = True

        # Create a task that stops after one frame
        async def run_one_frame():
            if runtime.is_dirty:
                await runtime._render_frame_async()
                runtime.running = False

        await run_one_frame()

    assert to_thread_called, "_render_frame should use asyncio.to_thread"
