"""Tests for click dispatch in TUIRuntime."""

import pytest

from wtfui.tui.renderer.input import MouseEvent
from wtfui.tui.runtime import TUIRuntime
from wtfui.ui.elements import Button, Div

click_count = 0


def counter_app():
    global click_count
    click_count = 0

    def on_click():
        global click_count
        click_count += 1

    with Div() as root:
        # Give button explicit width so it's hittable (otherwise width=0)
        Button("Click me", on_click=on_click, width=10, height=3)
    return root


class TestClickDispatch:
    """Test mouse click dispatch to element handlers."""

    @pytest.mark.asyncio
    async def test_click_on_button_calls_handler(self):
        """Clicking on a button should invoke its on_click handler."""
        global click_count

        runtime = TUIRuntime(app_factory=counter_app, fps=60)
        runtime.running = True

        # Build element tree and layout
        runtime.element_tree = counter_app()
        runtime._update_layout()

        # Find button's layout bounds
        button_layout = runtime.layout_root.children[0]  # First child is button
        center_x = button_layout.layout.x + button_layout.layout.width / 2
        center_y = button_layout.layout.y + button_layout.layout.height / 2

        # Simulate mouse press
        event = MouseEvent(x=int(center_x), y=int(center_y), button=0, pressed=True)
        await runtime._handle_event(event)

        assert click_count == 1

    @pytest.mark.asyncio
    async def test_click_outside_button_does_not_call_handler(self):
        """Clicking outside a button should not invoke its handler."""
        global click_count

        runtime = TUIRuntime(app_factory=counter_app, fps=60)
        runtime.running = True
        runtime.element_tree = counter_app()
        runtime._update_layout()

        # Click outside the layout bounds
        event = MouseEvent(x=1000, y=1000, button=0, pressed=True)
        await runtime._handle_event(event)

        assert click_count == 0


async_click_count = 0


def async_counter_app():
    global async_click_count
    async_click_count = 0

    async def on_click():
        global async_click_count
        async_click_count += 1

    with Div() as root:
        Button("Async Click", on_click=on_click, width=10, height=3)
    return root


class TestAsyncClickDispatch:
    """Test async click handler dispatch."""

    @pytest.mark.asyncio
    async def test_async_click_handler_awaited(self):
        """Async click handlers should be properly awaited."""
        global async_click_count

        runtime = TUIRuntime(app_factory=async_counter_app, fps=60)
        runtime.running = True
        runtime.element_tree = async_counter_app()
        runtime._update_layout()

        button_layout = runtime.layout_root.children[0]
        center_x = button_layout.layout.x + button_layout.layout.width / 2
        center_y = button_layout.layout.y + button_layout.layout.height / 2

        event = MouseEvent(x=int(center_x), y=int(center_y), button=0, pressed=True)
        await runtime._handle_event(event)

        assert async_click_count == 1
