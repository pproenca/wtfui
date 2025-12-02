# tests/test_console_terminal.py
"""Tests for terminal utilities."""

from unittest.mock import MagicMock, patch

from flow.renderer.console.terminal import (
    TerminalContext,
    get_terminal_size,
)


def test_get_terminal_size_returns_tuple():
    """get_terminal_size returns (width, height) tuple."""
    size = get_terminal_size()
    assert isinstance(size, tuple)
    assert len(size) == 2
    width, height = size
    assert isinstance(width, int)
    assert isinstance(height, int)


def test_get_terminal_size_has_reasonable_defaults():
    """Terminal size has reasonable minimums."""
    width, height = get_terminal_size()
    assert width >= 1
    assert height >= 1


def test_terminal_context_manager():
    """TerminalContext provides setup/teardown."""
    # Just test it doesn't crash (actual terminal setup needs a TTY)
    ctx = TerminalContext(width=80, height=24)
    assert ctx.width == 80
    assert ctx.height == 24


@patch("flow.renderer.console.terminal.os.get_terminal_size")
def test_get_terminal_size_uses_os_call(mock_get_size):
    """Uses os.get_terminal_size when available."""
    mock_get_size.return_value = MagicMock(columns=120, lines=40)

    width, height = get_terminal_size()

    mock_get_size.assert_called()
    assert width == 120
    assert height == 40
