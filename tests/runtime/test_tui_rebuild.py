"""Tests for TUIRuntime tree rebuild mechanism."""

import pytest

from wtfui import component
from wtfui.tui.testing import TUITestDriver
from wtfui.ui import Div, Text


@component
def rebuild_test_app():
    """App that will trigger structural changes."""
    with Div(width=60, height=10) as root:
        Text("Initial")
    return root


class TestTUIRebuild:
    """TUIRuntime can rebuild reactive tree on demand."""

    @pytest.mark.asyncio
    async def test_runtime_has_needs_rebuild_flag(self):
        """Runtime should have needs_rebuild attribute."""
        driver = TUITestDriver(rebuild_test_app, width=60, height=10)
        await driver.start()

        assert hasattr(driver.runtime, "needs_rebuild")
        assert driver.runtime.needs_rebuild is False

    @pytest.mark.asyncio
    async def test_needs_rebuild_triggers_tree_rebuild(self):
        """Setting needs_rebuild should rebuild reactive tree."""
        driver = TUITestDriver(rebuild_test_app, width=60, height=10)
        await driver.start()

        # Get reference to original reactive tree
        original_reactive = driver.runtime.reactive_layout

        # Modify element tree (simulating For adding a child)
        new_text = Text("Added")
        new_text.parent = driver.runtime.element_tree
        driver.runtime.element_tree.children.append(new_text)

        # Trigger rebuild
        driver.runtime.needs_rebuild = True
        await driver.stabilize()

        # Reactive tree should be rebuilt (new instance)
        assert driver.runtime.reactive_layout is not original_reactive
        # New child should be in snapshot
        snapshot = driver.snapshot()
        assert "Added" in snapshot
