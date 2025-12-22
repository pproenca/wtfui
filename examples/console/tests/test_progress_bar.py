"""Tests for ProgressBar component using TUITestDriver."""

import pytest
from components.progress_bar import ProgressBar

from wtfui.tui.testing import TUITestDriver
from wtfui.ui.elements import Div


def progress_bar_app():
    """App factory that renders a ProgressBar with known value."""
    with Div(width=40, height=5) as root:
        ProgressBar(value=75.0, color="green")
    return root


class TestProgressBarRendering:
    """Test ProgressBar renders correctly."""

    @pytest.mark.asyncio
    async def test_progress_bar_shows_percentage(self):
        """ProgressBar should display the percentage value."""
        driver = TUITestDriver(progress_bar_app, width=40, height=10)
        await driver.start()

        snapshot = driver.snapshot()

        # Should show "75.0%" in the output
        assert "75.0%" in snapshot

    @pytest.mark.asyncio
    async def test_progress_bar_shows_bar_chars(self):
        """ProgressBar should render filled and empty bar characters."""
        driver = TUITestDriver(progress_bar_app, width=40, height=10)
        await driver.start()

        snapshot = driver.snapshot()

        # Bar uses filled and empty characters
        # At 75% of 20 chars = 15 filled
        assert "\u2588" in snapshot or "█" in snapshot  # Filled block
        assert "\u2591" in snapshot or "░" in snapshot  # Empty block
