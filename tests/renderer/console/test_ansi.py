"""Tests for ANSI escape sequence generation."""

from wtfui.tui.renderer.ansi import (
    clear_screen,
    cursor_hide,
    cursor_move,
    cursor_show,
    disable_mouse_tracking,
    enable_mouse_tracking,
    reset_style,
    set_bg_rgb,
    set_bold,
    set_dim,
    set_fg_rgb,
)

# --- Cursor and Screen Tests ---


def test_cursor_move():
    """Move cursor to (col, row) using 1-based ANSI coordinates."""
    # ANSI uses 1-based indexing, (row;col)
    assert cursor_move(0, 0) == "\x1b[1;1H"
    assert cursor_move(10, 5) == "\x1b[6;11H"


def test_cursor_hide_show():
    """Hide and show cursor."""
    assert cursor_hide() == "\x1b[?25l"
    assert cursor_show() == "\x1b[?25h"


def test_clear_screen():
    """Clear entire screen."""
    assert clear_screen() == "\x1b[2J"


def test_clear_from_cursor_down():
    """Clear from cursor position to end of screen."""
    from wtfui.tui.renderer.ansi import clear_from_cursor_down

    # ANSI escape sequence: ESC[J or ESC[0J clears from cursor to end of screen
    assert clear_from_cursor_down() == "\x1b[J"


# --- Color Tests ---


def test_set_fg_rgb():
    """Set foreground color using 24-bit RGB."""
    assert set_fg_rgb(255, 0, 0) == "\x1b[38;2;255;0;0m"
    assert set_fg_rgb(0, 255, 128) == "\x1b[38;2;0;255;128m"


def test_set_bg_rgb():
    """Set background color using 24-bit RGB."""
    assert set_bg_rgb(0, 0, 255) == "\x1b[48;2;0;0;255m"


def test_reset_style():
    """Reset all style attributes."""
    assert reset_style() == "\x1b[0m"


def test_set_bold():
    """Enable bold text."""
    assert set_bold() == "\x1b[1m"


def test_set_dim():
    """Enable dim text."""
    assert set_dim() == "\x1b[2m"


# --- Mouse Tracking Tests ---


def test_enable_mouse_tracking():
    """Enable mouse tracking should emit correct ANSI sequences."""
    seq = enable_mouse_tracking()

    # Should enable: basic (1000), motion (1003), SGR mode (1006)
    assert "\x1b[?1000h" in seq  # Basic mouse tracking
    assert "\x1b[?1003h" in seq  # Any-event tracking (motion)
    assert "\x1b[?1006h" in seq  # SGR extended mode


def test_disable_mouse_tracking():
    """Disable mouse tracking should reset all mouse modes."""
    seq = disable_mouse_tracking()

    assert "\x1b[?1006l" in seq
    assert "\x1b[?1003l" in seq
    assert "\x1b[?1000l" in seq


# --- Terminal Reset Tests ---


def test_cursor_home():
    """Move cursor to home position (0, 0)."""
    from wtfui.tui.renderer.ansi import cursor_home

    # CSI H moves cursor to home (row 1, column 1)
    assert cursor_home() == "\x1b[H"


def test_reset_scroll_region():
    """Reset scroll region to full screen (DECSTBM)."""
    from wtfui.tui.renderer.ansi import reset_scroll_region

    # CSI r resets DECSTBM (scroll region) to full screen
    assert reset_scroll_region() == "\x1b[r"
