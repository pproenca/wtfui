# tests/renderer/console/test_terminal.py
"""Tests for terminal utilities and context manager."""

from unittest.mock import MagicMock, patch

from wtfui.tui.renderer.terminal import (
    TerminalContext,
    get_terminal_size,
)

# --- Terminal Size Tests ---


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


@patch("wtfui.tui.renderer.terminal.os.get_terminal_size")
def test_get_terminal_size_uses_os_call(mock_get_size):
    """Uses os.get_terminal_size when available."""
    mock_get_size.return_value = MagicMock(columns=120, lines=40)

    width, height = get_terminal_size()

    mock_get_size.assert_called()
    assert width == 120
    assert height == 40


# --- Terminal Context Tests ---


def test_terminal_context_manager():
    """TerminalContext provides setup/teardown."""
    # Just test it doesn't crash (actual terminal setup needs a TTY)
    ctx = TerminalContext(width=80, height=24)
    assert ctx.width == 80
    assert ctx.height == 24


def test_terminal_context_enables_mouse():
    """TerminalContext should enable mouse tracking on enter."""
    with (
        patch("sys.stdout") as mock_stdout,
        patch("sys.stdin") as mock_stdin,
        patch("wtfui.tui.renderer.terminal.setup_raw_mode"),
    ):
        mock_stdin.isatty.return_value = True
        mock_stdout.write = MagicMock()
        mock_stdout.flush = MagicMock()

        ctx = TerminalContext(width=80, height=24, mouse=True)
        ctx.__enter__()

        # Check that mouse tracking was enabled
        all_writes = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
        assert "\x1b[?1000h" in all_writes  # Mouse tracking enabled


def test_terminal_context_disables_mouse_on_exit():
    """TerminalContext should disable mouse tracking on exit."""
    with (
        patch("sys.stdout") as mock_stdout,
        patch("sys.stdin") as mock_stdin,
        patch("wtfui.tui.renderer.terminal.restore_terminal"),
    ):
        mock_stdin.isatty.return_value = True
        mock_stdout.write = MagicMock()
        mock_stdout.flush = MagicMock()

        ctx = TerminalContext(width=80, height=24, mouse=True)
        ctx._setup_done = True  # Simulate __enter__ was called
        ctx.__exit__(None, None, None)

        all_writes = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
        assert "\x1b[?1000l" in all_writes  # Mouse tracking disabled


# --- Inline Mode Tests ---


def test_terminal_context_inline_skips_alt_screen():
    """Inline mode should NOT enter alternate screen buffer."""
    with (
        patch("sys.stdout") as mock_stdout,
        patch("sys.stdin") as mock_stdin,
        patch("wtfui.tui.renderer.terminal.setup_raw_mode"),
    ):
        mock_stdin.isatty.return_value = True
        mock_stdout.write = MagicMock()
        mock_stdout.flush = MagicMock()

        ctx = TerminalContext(width=80, height=24, inline=True)
        ctx.__enter__()

        all_writes = "".join(call.args[0] for call in mock_stdout.write.call_args_list)

        # Should NOT contain alt screen escape sequence
        assert "\x1b[?1049h" not in all_writes, "Inline mode should not enter alt screen"
        # Should still hide cursor
        assert "\x1b[?25l" in all_writes, "Inline mode should still hide cursor"


def test_terminal_context_inline_skips_clear_screen():
    """Inline mode should NOT clear the screen on enter."""
    with (
        patch("sys.stdout") as mock_stdout,
        patch("sys.stdin") as mock_stdin,
        patch("wtfui.tui.renderer.terminal.setup_raw_mode"),
    ):
        mock_stdin.isatty.return_value = True
        mock_stdout.write = MagicMock()
        mock_stdout.flush = MagicMock()

        ctx = TerminalContext(width=80, height=24, inline=True)
        ctx.__enter__()

        all_writes = "".join(call.args[0] for call in mock_stdout.write.call_args_list)

        # Should NOT contain clear screen escape sequence
        assert "\x1b[2J" not in all_writes, "Inline mode should not clear screen"


def test_terminal_context_default_uses_alt_screen():
    """Default mode (inline=False) should use alternate screen."""
    with (
        patch("sys.stdout") as mock_stdout,
        patch("sys.stdin") as mock_stdin,
        patch("wtfui.tui.renderer.terminal.setup_raw_mode"),
    ):
        mock_stdin.isatty.return_value = True
        mock_stdout.write = MagicMock()
        mock_stdout.flush = MagicMock()

        ctx = TerminalContext(width=80, height=24, alt_screen=True)
        ctx.__enter__()

        all_writes = "".join(call.args[0] for call in mock_stdout.write.call_args_list)

        # Should contain alt screen sequence
        assert "\x1b[?1049h" in all_writes, "Default mode should enter alt screen"


# --- Terminal Reset for Shell Compatibility ---


def test_terminal_context_resets_scroll_region():
    """TerminalContext should reset scroll region before clear for shell compatibility."""
    with (
        patch("sys.stdout") as mock_stdout,
        patch("sys.stdin") as mock_stdin,
        patch("wtfui.tui.renderer.terminal.setup_raw_mode"),
    ):
        mock_stdin.isatty.return_value = True
        mock_stdout.write = MagicMock()
        mock_stdout.flush = MagicMock()

        ctx = TerminalContext(width=80, height=24, alt_screen=True)
        ctx.__enter__()

        all_writes = "".join(call.args[0] for call in mock_stdout.write.call_args_list)

        # Should contain scroll region reset (DECSTBM)
        assert "\x1b[r" in all_writes, "Should reset scroll region for shell compatibility"


def test_terminal_context_cursor_home_after_clear():
    """Cursor home should follow clear screen for predictable positioning."""
    with (
        patch("sys.stdout") as mock_stdout,
        patch("sys.stdin") as mock_stdin,
        patch("wtfui.tui.renderer.terminal.setup_raw_mode"),
    ):
        mock_stdin.isatty.return_value = True
        mock_stdout.write = MagicMock()
        mock_stdout.flush = MagicMock()

        ctx = TerminalContext(width=80, height=24, alt_screen=True)
        ctx.__enter__()

        all_writes = "".join(call.args[0] for call in mock_stdout.write.call_args_list)

        # Should contain cursor home
        assert "\x1b[H" in all_writes, "Should move cursor home after clear"

        # Cursor home should follow clear screen
        clear_idx = all_writes.index("\x1b[2J")
        home_idx = all_writes.index("\x1b[H")
        assert home_idx > clear_idx, "Cursor home should follow clear screen"


def test_terminal_context_scroll_region_before_clear():
    """Scroll region reset should precede clear screen."""
    with (
        patch("sys.stdout") as mock_stdout,
        patch("sys.stdin") as mock_stdin,
        patch("wtfui.tui.renderer.terminal.setup_raw_mode"),
    ):
        mock_stdin.isatty.return_value = True
        mock_stdout.write = MagicMock()
        mock_stdout.flush = MagicMock()

        ctx = TerminalContext(width=80, height=24, alt_screen=True)
        ctx.__enter__()

        all_writes = "".join(call.args[0] for call in mock_stdout.write.call_args_list)

        # Scroll region reset should come before clear screen
        reset_idx = all_writes.index("\x1b[r")
        clear_idx = all_writes.index("\x1b[2J")
        assert reset_idx < clear_idx, "Scroll region reset should precede clear screen"
