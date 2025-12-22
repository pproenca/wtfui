"""Tests for TUITestDriver - the main testing API."""

import pytest

from wtfui.ui.elements import Button, Div, Text


def simple_app():
    with Div() as root:
        Text("Hello World")
    return root


click_count = 0


def counter_app():
    global click_count
    click_count = 0

    def on_click():
        global click_count
        click_count += 1

    with Div() as root:
        # Elements need explicit width for rendering (intrinsic sizing not yet implemented)
        Text(f"Count: {click_count}", width=15)
        Button("Increment", on_click=on_click, width=15)
    return root


class TestTUITestDriverInit:
    """Test TUITestDriver initialization."""

    @pytest.mark.asyncio
    async def test_driver_accepts_app_factory(self):
        """TUITestDriver should accept an app factory."""
        from wtfui.tui.testing import TUITestDriver

        driver = TUITestDriver(simple_app)
        assert driver is not None

    @pytest.mark.asyncio
    async def test_driver_has_start_method(self):
        """TUITestDriver should have a start() method."""
        from wtfui.tui.testing import TUITestDriver

        driver = TUITestDriver(simple_app)
        assert hasattr(driver, "start")
        assert callable(driver.start)

    @pytest.mark.asyncio
    async def test_start_initializes_runtime(self):
        """start() should initialize the runtime and render."""
        from wtfui.tui.testing import TUITestDriver

        driver = TUITestDriver(simple_app)
        await driver.start()

        assert driver.runtime is not None
        assert driver.runtime.element_tree is not None


class TestTUITestDriverSnapshot:
    """Test snapshot functionality."""

    @pytest.mark.asyncio
    async def test_snapshot_returns_rendered_content(self):
        """snapshot() should return the rendered text."""
        from wtfui.tui.testing import TUITestDriver

        driver = TUITestDriver(simple_app, width=40, height=10)
        await driver.start()

        result = driver.snapshot()

        assert "Hello World" in result


class TestTUITestDriverGetByText:
    """Test semantic locator integration."""

    @pytest.mark.asyncio
    async def test_get_by_text_finds_element(self):
        """get_by_text() should return a locator for the element."""
        from wtfui.tui.testing import TUITestDriver

        driver = TUITestDriver(simple_app, width=40, height=10)
        await driver.start()

        locator = driver.get_by_text("Hello World")

        assert locator is not None


class TestTUITestDriverClick:
    """Test click interaction."""

    @pytest.mark.asyncio
    async def test_click_on_button_invokes_handler(self):
        """Clicking a button should invoke its on_click handler."""
        global click_count
        from wtfui.tui.testing import TUITestDriver

        driver = TUITestDriver(counter_app, width=40, height=10)
        await driver.start()

        # Get the button locator and click
        button = driver.get_by_text("Increment")
        await button.click()

        assert click_count == 1

    @pytest.mark.asyncio
    async def test_click_stabilizes_after_handler(self):
        """Click should auto-wait for effects to settle."""
        global click_count
        from wtfui.tui.testing import TUITestDriver

        driver = TUITestDriver(counter_app, width=40, height=10)
        await driver.start()

        button = driver.get_by_text("Increment")
        await button.click()
        await button.click()

        # Effects should have settled
        assert click_count == 2


class TestTUITestDriverStabilize:
    """Test stabilization API."""

    @pytest.mark.asyncio
    async def test_stabilize_waits_for_effects(self):
        """stabilize() should wait for all pending effects."""
        from wtfui.tui.testing import TUITestDriver

        driver = TUITestDriver(simple_app, width=40, height=10)
        await driver.start()

        result = await driver.stabilize()

        assert result is True


class TestTUITestDriverIntegration:
    """Full integration tests for realistic scenarios."""

    @pytest.mark.asyncio
    async def test_counter_app_full_flow(self):
        """Test complete counter app interaction."""
        global click_count
        from wtfui.tui.testing import TUITestDriver

        driver = TUITestDriver(counter_app, width=40, height=10)
        await driver.start()

        # Verify initial state via snapshot
        snap = driver.snapshot()
        assert "Count:" in snap
        assert "Increment" in snap

        # Click increment button
        await driver.get_by_text("Increment").click()

        # Verify handler was called
        assert click_count == 1
