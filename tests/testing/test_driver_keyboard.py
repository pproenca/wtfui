"""Tests for TUITestDriver keyboard input support."""

import pytest

from wtfui.tui.testing import TUITestDriver
from wtfui.ui.elements import Div, Text

# Global to capture typed keys for testing
typed_keys: list[str] = []


def keyboard_capture_app():
    """App that captures keyboard input via on_key callback."""
    global typed_keys
    typed_keys = []

    with Div(width=40, height=5) as root:
        Text("Type test", width=40)
    return root


class TestTUITestDriverKeyboard:
    """Test keyboard input support."""

    @pytest.mark.asyncio
    async def test_driver_has_type_method(self):
        """TUITestDriver should have a type() method."""
        driver = TUITestDriver(keyboard_capture_app, width=40, height=10)
        await driver.start()

        assert hasattr(driver, "type")
        assert callable(driver.type)

    @pytest.mark.asyncio
    async def test_driver_has_press_method(self):
        """TUITestDriver should have a press() method."""
        driver = TUITestDriver(keyboard_capture_app, width=40, height=10)
        await driver.start()

        assert hasattr(driver, "press")
        assert callable(driver.press)

    @pytest.mark.asyncio
    async def test_type_sends_key_events(self):
        """type() should send KeyEvents through the runtime."""
        global typed_keys
        typed_keys = []

        def on_key(key: str) -> None:
            typed_keys.append(key)

        driver = TUITestDriver(keyboard_capture_app, width=40, height=10)
        await driver.start()
        driver.runtime.on_key = on_key

        await driver.type("abc")

        assert typed_keys == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_press_q_stops_runtime(self):
        """Pressing 'q' should stop the runtime (built-in quit)."""
        driver = TUITestDriver(keyboard_capture_app, width=40, height=10)
        await driver.start()

        assert driver.runtime.running is True

        await driver.press("q")

        assert driver.runtime.running is False
