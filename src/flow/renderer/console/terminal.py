# src/flow/renderer/console/terminal.py
"""Terminal utilities for console rendering."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import TracebackType

# Store original terminal settings for restoration
_original_termios: Any = None


def get_terminal_size() -> tuple[int, int]:
    """Get current terminal size.

    Returns:
        Tuple of (width, height) in characters.
    """
    try:
        size = os.get_terminal_size()
        return (size.columns, size.lines)
    except OSError:
        # Fallback for non-TTY (e.g., piped input)
        return (80, 24)


def setup_raw_mode() -> None:
    """Put terminal in raw mode for character-by-character input.

    Raw mode disables:
    - Line buffering (input available immediately)
    - Echo (typed chars not shown)
    - Signal generation (Ctrl+C doesn't raise SIGINT)
    """
    global _original_termios

    if not sys.stdin.isatty():
        return

    try:
        import termios
        import tty

        fd = sys.stdin.fileno()
        _original_termios = termios.tcgetattr(fd)
        tty.setraw(fd)
    except (ImportError, termios.error):
        pass


def restore_terminal() -> None:
    """Restore terminal to original settings."""
    global _original_termios

    if _original_termios is None:
        return

    if not sys.stdin.isatty():
        return

    try:
        import termios

        fd = sys.stdin.fileno()
        termios.tcsetattr(fd, termios.TCSADRAIN, _original_termios)
        _original_termios = None
    except (ImportError, termios.error):
        pass


class TerminalContext:
    """Context manager for terminal-mode applications.

    Handles:
    - Entering alternate screen buffer
    - Raw mode setup
    - Cleanup on exit

    Usage:
        with TerminalContext() as ctx:
            renderer = ConsoleRenderer(ctx.width, ctx.height)
            # ... render loop
    """

    def __init__(
        self,
        width: int | None = None,
        height: int | None = None,
        alt_screen: bool = True,
    ) -> None:
        """Initialize terminal context.

        Args:
            width: Override width (uses terminal size if None).
            height: Override height (uses terminal size if None).
            alt_screen: Whether to use alternate screen buffer.
        """
        detected_w, detected_h = get_terminal_size()
        self.width = width if width is not None else detected_w
        self.height = height if height is not None else detected_h
        self.alt_screen = alt_screen
        self._setup_done = False

    def __enter__(self) -> TerminalContext:
        """Enter terminal mode."""
        from flow.renderer.console import ansi

        if self.alt_screen:
            sys.stdout.write(ansi.enter_alt_screen())

        sys.stdout.write(ansi.cursor_hide())
        sys.stdout.write(ansi.clear_screen())
        sys.stdout.flush()

        setup_raw_mode()
        self._setup_done = True

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit terminal mode and restore settings."""
        from flow.renderer.console import ansi

        restore_terminal()

        sys.stdout.write(ansi.cursor_show())
        sys.stdout.write(ansi.reset_style())

        if self.alt_screen:
            sys.stdout.write(ansi.exit_alt_screen())

        sys.stdout.flush()
