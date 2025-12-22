import os
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import TracebackType


_original_termios: Any = None


def get_terminal_size() -> tuple[int, int]:
    try:
        size = os.get_terminal_size()
        return (size.columns, size.lines)
    except OSError:
        return (80, 24)


def setup_raw_mode() -> None:
    global _original_termios

    if not sys.stdin.isatty():
        return

    try:
        import termios
        import tty
    except ImportError:
        return

    try:
        fd = sys.stdin.fileno()
        _original_termios = termios.tcgetattr(fd)
        tty.setraw(fd)
    except termios.error:
        pass


def restore_terminal() -> None:
    global _original_termios

    if _original_termios is None:
        return

    if not sys.stdin.isatty():
        return

    try:
        import termios
    except ImportError:
        return

    try:
        fd = sys.stdin.fileno()
        termios.tcsetattr(fd, termios.TCSADRAIN, _original_termios)
        _original_termios = None
    except termios.error:
        pass


class TerminalContext:
    def __init__(
        self,
        width: int | None = None,
        height: int | None = None,
        alt_screen: bool = True,
        mouse: bool = False,
        inline: bool = False,
    ) -> None:
        detected_w, detected_h = get_terminal_size()
        self.width = width if width is not None else detected_w
        self.height = height if height is not None else detected_h

        self.alt_screen = False if inline else alt_screen
        self.mouse = mouse
        self.inline = inline
        self._setup_done = False

    def __enter__(self) -> TerminalContext:
        from wtfui.tui.renderer import ansi

        if self.alt_screen:
            sys.stdout.write(ansi.enter_alt_screen())

        sys.stdout.write(ansi.cursor_hide())

        if not self.inline:
            sys.stdout.write(ansi.reset_scroll_region())
            sys.stdout.write(ansi.clear_screen())
            sys.stdout.write(ansi.cursor_home())

        if self.mouse:
            sys.stdout.write(ansi.enable_mouse_tracking())

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
        from wtfui.tui.renderer import ansi

        restore_terminal()

        if self.mouse:
            sys.stdout.write(ansi.disable_mouse_tracking())

        sys.stdout.write(ansi.cursor_show())
        sys.stdout.write(ansi.reset_style())

        if self.alt_screen:
            sys.stdout.write(ansi.exit_alt_screen())

        sys.stdout.flush()
