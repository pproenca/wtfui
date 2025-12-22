# tests/renderer/console/test_input.py
"""Tests for console input handling (keyboard and mouse)."""

from wtfui.tui.renderer.input import (
    CTRL_C,
    CTRL_O,
    ESCAPE,
    KeyEvent,
    MouseEvent,
    parse_input_sequence,
    parse_key_sequence,
)

# --- Keyboard Input Tests ---


def test_key_event_creation():
    """KeyEvent holds key information."""
    event = KeyEvent(key="a", ctrl=False, alt=False)
    assert event.key == "a"
    assert event.ctrl is False


def test_parse_regular_key():
    """Regular keys are parsed directly."""
    event = parse_key_sequence("a")
    assert event.key == "a"
    assert event.ctrl is False


def test_parse_ctrl_key():
    """Ctrl+key combinations are detected."""
    event = parse_key_sequence(CTRL_O)  # Ctrl+O = \x0f
    assert event.key == "o"
    assert event.ctrl is True


def test_parse_ctrl_c():
    """Ctrl+C is parsed correctly."""
    event = parse_key_sequence(CTRL_C)  # \x03
    assert event.key == "c"
    assert event.ctrl is True


def test_parse_escape():
    """Escape key is recognized."""
    event = parse_key_sequence(ESCAPE)
    assert event.key == "escape"


def test_parse_arrow_up():
    """Arrow up sequence is parsed."""
    event = parse_key_sequence("\x1b[A")
    assert event.key == "up"


def test_parse_arrow_down():
    """Arrow down sequence is parsed."""
    event = parse_key_sequence("\x1b[B")
    assert event.key == "down"


def test_parse_enter():
    """Enter key (CR/LF) is recognized."""
    event = parse_key_sequence("\r")
    assert event.key == "enter"


# --- Mouse Input Tests (SGR 1006) ---


class TestMouseEventParsing:
    """Test SGR 1006 mouse sequence parsing."""

    def test_parse_mouse_click_press(self):
        """Parse SGR 1006 mouse button press."""
        # ESC[<0;10;5M = Button 1 press at column 10, row 5
        seq = "\x1b[<0;10;5M"
        event = parse_input_sequence(seq)

        assert isinstance(event, MouseEvent)
        assert event.x == 9  # 0-indexed (column 10 -> index 9)
        assert event.y == 4  # 0-indexed (row 5 -> index 4)
        assert event.button == 0  # Left button
        assert event.pressed is True

    def test_parse_mouse_click_release(self):
        """Parse SGR 1006 mouse button release."""
        # ESC[<0;10;5m = Button 1 release (lowercase m)
        seq = "\x1b[<0;10;5m"
        event = parse_input_sequence(seq)

        assert isinstance(event, MouseEvent)
        assert event.pressed is False

    def test_parse_mouse_move(self):
        """Parse mouse move event (button 35 = move with no buttons)."""
        # ESC[<35;20;10M = Mouse move to column 20, row 10
        seq = "\x1b[<35;20;10M"
        event = parse_input_sequence(seq)

        assert isinstance(event, MouseEvent)
        assert event.x == 19
        assert event.y == 9
        assert event.is_move is True

    def test_keyboard_still_works(self):
        """Keyboard events should still parse correctly."""
        event = parse_input_sequence("a")
        assert isinstance(event, KeyEvent)
        assert event.key == "a"

        event = parse_input_sequence("\x1b[A")
        assert isinstance(event, KeyEvent)
        assert event.key == "up"
