"""Tests for ProcessList component using TUITestDriver.

These tests validate the reactive pipeline:
Signal(filter_text) → Computed(filtered_procs) → Layout → Render
"""

import pytest
from components.process_list import ProcessList
from state import SystemState

from wtfui.tui.testing import TUITestDriver
from wtfui.ui.elements import Div

# Keep state accessible for signal manipulation
test_state: SystemState | None = None


def process_list_app():
    """App factory with pre-populated process data."""
    global test_state
    test_state = SystemState()
    # Set up mock process data
    test_state.processes.value = [
        {"pid": 123, "name": "python", "cpu_percent": 15.0},
        {"pid": 456, "name": "chrome", "cpu_percent": 8.5},
        {"pid": 789, "name": "vscode", "cpu_percent": 5.0},
    ]

    with Div(width=60, height=15) as root:
        ProcessList(test_state)
    return root


class TestProcessListRendering:
    """Test ProcessList renders correctly."""

    @pytest.mark.asyncio
    async def test_process_list_shows_header(self):
        """ProcessList should show column headers."""
        driver = TUITestDriver(process_list_app, width=60, height=20)
        await driver.start()

        snapshot = driver.snapshot()

        assert "PID" in snapshot
        assert "Name" in snapshot
        assert "CPU%" in snapshot

    @pytest.mark.asyncio
    async def test_process_list_shows_all_processes(self):
        """ProcessList should display all process information."""
        driver = TUITestDriver(process_list_app, width=60, height=20)
        await driver.start()

        snapshot = driver.snapshot()

        # All processes should be visible initially
        assert "python" in snapshot
        assert "chrome" in snapshot
        assert "vscode" in snapshot


class TestProcessListFiltering:
    """Test ProcessList filtering via Signal updates.

    This tests the REACTIVE PIPELINE - the core of Flow:
    Signal(filter_text) → Computed(filtered_procs) → Layout → Render

    NOTE: We update the Signal directly because the Input component
    doesn't receive keyboard events (no focus system yet).
    """

    @pytest.mark.asyncio
    async def test_filter_hides_non_matching_processes(self):
        """Setting filter_text Signal should hide non-matching processes.

        The For component enables reactive list updates - when filter_text
        changes, the Computed chain re-evaluates and For updates its children.

        This tests the full reactive pipeline:
        Signal(filter_text) → Computed(filtered_procs) → Computed(limited_procs) → For
        """
        global test_state
        driver = TUITestDriver(process_list_app, width=60, height=20)
        await driver.start()

        # Initially all visible
        snapshot = driver.snapshot()
        assert "python" in snapshot
        assert "chrome" in snapshot

        # Update filter via Signal (simulates what Input component would do)
        test_state.filter_text.value = "py"
        await driver.stabilize()

        # After filter, only "python" should be visible
        snapshot = driver.snapshot()
        assert "python" in snapshot
        assert "chrome" not in snapshot
        assert "vscode" not in snapshot

    @pytest.mark.asyncio
    async def test_filter_is_case_insensitive(self):
        """Filter should match case-insensitively."""
        global test_state
        driver = TUITestDriver(process_list_app, width=60, height=20)
        await driver.start()

        test_state.filter_text.value = "PYTHON"
        await driver.stabilize()

        snapshot = driver.snapshot()
        assert "python" in snapshot

    @pytest.mark.asyncio
    async def test_clear_filter_shows_all(self):
        """Clearing filter should show all processes again."""
        global test_state
        driver = TUITestDriver(process_list_app, width=60, height=20)
        await driver.start()

        # Set filter
        test_state.filter_text.value = "python"
        await driver.stabilize()

        # Clear filter
        test_state.filter_text.value = ""
        await driver.stabilize()

        snapshot = driver.snapshot()
        assert "python" in snapshot
        assert "chrome" in snapshot
        assert "vscode" in snapshot
