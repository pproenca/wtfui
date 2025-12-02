# tests/test_console_ansi.py
"""Tests for ANSI escape sequence generation."""

from flow.renderer.console.ansi import (
    clear_screen,
    cursor_hide,
    cursor_move,
    cursor_show,
    reset_style,
    set_bg_rgb,
    set_bold,
    set_dim,
    set_fg_rgb,
)


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
