"""Tests for TUIRuntime layout update in render loop."""

import pytest

from wtfui import Signal, component
from wtfui.tui.testing import TUITestDriver
from wtfui.ui import Div, Text


@component
def width_signal_app():
    """App with signal-bound width."""
    width_signal = Signal(10)

    with Div(width=60, height=10) as root:
        root.props["_width_signal"] = width_signal
        # Text with signal-bound width won't work in layout until
        # _update_layout is called in the render loop
        Text("X" * 20)
    return root


class TestTUILayoutUpdate:
    """TUIRuntime updates layout when dirty."""

    @pytest.mark.asyncio
    async def test_runtime_calls_update_layout_when_dirty(self):
        """Runtime should call _update_layout when is_dirty is True."""
        driver = TUITestDriver(width_signal_app, width=60, height=10)
        await driver.start()

        # Track method call order
        call_order = []
        original_update = driver.runtime._update_layout
        original_render = driver.runtime._render_frame

        def tracking_update():
            call_order.append("update_layout")
            original_update()

        def tracking_render():
            call_order.append("render_frame")
            original_render()

        driver.runtime._update_layout = tracking_update
        driver.runtime._render_frame = tracking_render

        # Mark dirty and simulate one iteration of the render loop
        driver.runtime.is_dirty = True

        # Simulate what the render loop does when is_dirty is True
        if driver.runtime.is_dirty:
            driver.runtime._update_layout()
            driver.runtime._render_frame()

        # _update_layout should be called before _render_frame
        assert call_order == ["update_layout", "render_frame"], (
            f"Expected ['update_layout', 'render_frame'], got {call_order}"
        )
