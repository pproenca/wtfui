# src/flow/renderer/console/input.py
"""Console input handling for stdin key events."""

from __future__ import annotations

from dataclasses import dataclass

# Common control characters
CTRL_C = "\x03"
CTRL_D = "\x04"
CTRL_O = "\x0f"  # Used for sub-terminal toggle
CTRL_Z = "\x1a"
ESCAPE = "\x1b"
ENTER = "\r"
BACKSPACE = "\x7f"


@dataclass
class KeyEvent:
    """Represents a keyboard input event.

    Attributes:
        key: The key pressed (character or special name).
        ctrl: Whether Ctrl was held.
        alt: Whether Alt was held.
        shift: Whether Shift was held.
    """

    key: str
    ctrl: bool = False
    alt: bool = False
    shift: bool = False


# ANSI escape sequences for special keys
ESCAPE_SEQUENCES: dict[str, str] = {
    "\x1b[A": "up",
    "\x1b[B": "down",
    "\x1b[C": "right",
    "\x1b[D": "left",
    "\x1b[H": "home",
    "\x1b[F": "end",
    "\x1b[3~": "delete",
    "\x1b[5~": "page_up",
    "\x1b[6~": "page_down",
    "\x1bOP": "f1",
    "\x1bOQ": "f2",
    "\x1bOR": "f3",
    "\x1bOS": "f4",
}


def parse_key_sequence(seq: str) -> KeyEvent:
    """Parse a key sequence into a KeyEvent.

    Args:
        seq: Raw bytes/string from stdin.

    Returns:
        Parsed KeyEvent.
    """
    if not seq:
        return KeyEvent(key="")

    # Check escape sequences first
    if seq in ESCAPE_SEQUENCES:
        return KeyEvent(key=ESCAPE_SEQUENCES[seq])

    # Single escape
    if seq == ESCAPE:
        return KeyEvent(key="escape")

    # Enter/Return
    if seq in ("\r", "\n"):
        return KeyEvent(key="enter")

    # Backspace
    if seq == BACKSPACE or seq == "\x08":
        return KeyEvent(key="backspace")

    # Tab
    if seq == "\t":
        return KeyEvent(key="tab")

    # Ctrl+key (ASCII 1-26 = Ctrl+A through Ctrl+Z)
    if len(seq) == 1:
        code = ord(seq)
        if 1 <= code <= 26:
            char = chr(code + 96)  # Convert to lowercase letter
            return KeyEvent(key=char, ctrl=True)

    # Regular character
    if len(seq) == 1:
        return KeyEvent(key=seq)

    # Unknown sequence
    return KeyEvent(key=seq)


async def read_key_async() -> str:
    """Read a key or escape sequence from stdin asynchronously.

    Returns:
        The raw key sequence string.

    Note:
        This requires terminal to be in raw mode.
        Use with InputLoop for proper setup.
    """
    import asyncio
    import sys

    loop = asyncio.get_event_loop()

    # Read first character
    char = await loop.run_in_executor(None, lambda: sys.stdin.read(1))

    if char == ESCAPE:
        # Might be escape sequence, try to read more
        try:
            # Set stdin to non-blocking temporarily
            import select

            if select.select([sys.stdin], [], [], 0.05)[0]:
                # More data available - likely escape sequence
                extra = ""
                while select.select([sys.stdin], [], [], 0.01)[0]:
                    extra += sys.stdin.read(1)
                return char + extra
        except Exception:  # noqa: S110
            # Ignore errors reading escape sequences
            pass

    return char
