# src/flow/renderer/console/ansi.py
"""ANSI escape sequence generators for terminal control.

References:
- https://en.wikipedia.org/wiki/ANSI_escape_code
- https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
"""

from __future__ import annotations

# Escape character
ESC = "\x1b"
CSI = f"{ESC}["  # Control Sequence Introducer


def cursor_move(x: int, y: int) -> str:
    """Move cursor to (x, y) position.

    Args:
        x: Column (0-based).
        y: Row (0-based).

    Returns:
        ANSI escape sequence (converts to 1-based internally).
    """
    # ANSI format: ESC[row;colH (1-based)
    return f"{CSI}{y + 1};{x + 1}H"


def cursor_hide() -> str:
    """Hide the cursor."""
    return f"{CSI}?25l"


def cursor_show() -> str:
    """Show the cursor."""
    return f"{CSI}?25h"


def clear_screen() -> str:
    """Clear the entire screen."""
    return f"{CSI}2J"


def clear_line() -> str:
    """Clear the current line."""
    return f"{CSI}2K"


def set_fg_rgb(r: int, g: int, b: int) -> str:
    """Set foreground color using 24-bit RGB (TrueColor).

    Args:
        r: Red component (0-255).
        g: Green component (0-255).
        b: Blue component (0-255).
    """
    return f"{CSI}38;2;{r};{g};{b}m"


def set_bg_rgb(r: int, g: int, b: int) -> str:
    """Set background color using 24-bit RGB (TrueColor).

    Args:
        r: Red component (0-255).
        g: Green component (0-255).
        b: Blue component (0-255).
    """
    return f"{CSI}48;2;{r};{g};{b}m"


def reset_style() -> str:
    """Reset all text attributes to defaults."""
    return f"{CSI}0m"


def set_bold() -> str:
    """Enable bold text."""
    return f"{CSI}1m"


def set_dim() -> str:
    """Enable dim/faint text."""
    return f"{CSI}2m"


def set_italic() -> str:
    """Enable italic text."""
    return f"{CSI}3m"


def set_underline() -> str:
    """Enable underlined text."""
    return f"{CSI}4m"


def enter_alt_screen() -> str:
    """Enter alternate screen buffer (used by TUI apps)."""
    return f"{CSI}?1049h"


def exit_alt_screen() -> str:
    """Exit alternate screen buffer."""
    return f"{CSI}?1049l"
