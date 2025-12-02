# tests/test_console_input.py
"""Tests for console input handling."""

from flow.renderer.console.input import (
    CTRL_C,
    CTRL_O,
    ESCAPE,
    KeyEvent,
    parse_key_sequence,
)


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
