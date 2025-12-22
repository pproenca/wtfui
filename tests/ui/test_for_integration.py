"""Integration tests for For component with TUITestDriver."""

import pytest

from wtfui import Signal, component
from wtfui.tui.testing import TUITestDriver
from wtfui.ui import Div, For, Text, VStack


@component
def dynamic_list_app():
    """App with dynamic list."""
    items = Signal(["Apple", "Banana", "Cherry"])

    # Store signal on the root for test access
    with Div(width=40, height=10) as root:
        root.props["_items_signal"] = items
        with VStack():
            Text("Fruits:")
            For(
                each=items,
                render=lambda item, idx: Text(f"- {item}"),
            )
    return root


class TestForIntegration:
    """For component renders correctly in TUI."""

    @pytest.mark.asyncio
    async def test_for_renders_in_tui(self):
        """For renders initial items in TUI snapshot."""
        driver = TUITestDriver(dynamic_list_app, width=40, height=10)
        await driver.start()

        snapshot = driver.snapshot()

        assert "Fruits:" in snapshot
        assert "Apple" in snapshot
        assert "Banana" in snapshot
        assert "Cherry" in snapshot

    @pytest.mark.asyncio
    async def test_for_updates_on_signal_change(self):
        """For updates TUI when signal changes."""
        driver = TUITestDriver(dynamic_list_app, width=40, height=10)
        await driver.start()

        # Get the signal from root element
        items_signal = driver.runtime.element_tree.props["_items_signal"]

        # Initial state
        snapshot = driver.snapshot()
        assert "Apple" in snapshot

        # Change signal
        items_signal.value = ["Orange", "Grape"]
        await driver.stabilize()

        # Verify update
        snapshot = driver.snapshot()
        assert "Orange" in snapshot
        assert "Grape" in snapshot
        assert "Apple" not in snapshot
        assert "Banana" not in snapshot
