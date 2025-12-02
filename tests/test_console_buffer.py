# tests/test_console_buffer.py
"""Tests for console Buffer - the terminal framebuffer."""

from flow.renderer.console.buffer import Buffer
from flow.renderer.console.cell import Cell


def test_buffer_creation():
    """Buffer initializes with given dimensions."""
    buf = Buffer(width=80, height=24)
    assert buf.width == 80
    assert buf.height == 24


def test_buffer_get_cell_default():
    """Unset cells return empty Cell."""
    buf = Buffer(width=10, height=5)
    cell = buf.get(0, 0)
    assert cell.char == " "
    assert cell.fg is None


def test_buffer_set_cell():
    """Can set a cell at position."""
    buf = Buffer(width=10, height=5)
    cell = Cell(char="X", fg=(255, 0, 0))
    buf.set(3, 2, cell)

    result = buf.get(3, 2)
    assert result.char == "X"
    assert result.fg == (255, 0, 0)


def test_buffer_out_of_bounds_get():
    """Out of bounds get returns default cell."""
    buf = Buffer(width=10, height=5)
    cell = buf.get(100, 100)
    assert cell.char == " "


def test_buffer_out_of_bounds_set():
    """Out of bounds set is silently ignored."""
    buf = Buffer(width=10, height=5)
    cell = Cell(char="X")
    buf.set(100, 100, cell)  # Should not raise


def test_buffer_clear():
    """Clear resets all cells to default."""
    buf = Buffer(width=10, height=5)
    buf.set(0, 0, Cell(char="A"))
    buf.set(5, 2, Cell(char="B"))

    buf.clear()

    assert buf.get(0, 0).char == " "
    assert buf.get(5, 2).char == " "


def test_buffer_write_text():
    """Write text horizontally starting at position."""
    buf = Buffer(width=20, height=5)
    buf.write_text(2, 1, "Hello", fg=(255, 255, 255))

    assert buf.get(2, 1).char == "H"
    assert buf.get(3, 1).char == "e"
    assert buf.get(4, 1).char == "l"
    assert buf.get(5, 1).char == "l"
    assert buf.get(6, 1).char == "o"
    assert buf.get(2, 1).fg == (255, 255, 255)


def test_buffer_clone():
    """Clone creates independent copy."""
    buf = Buffer(width=10, height=5)
    buf.set(0, 0, Cell(char="X"))

    clone = buf.clone()
    clone.set(0, 0, Cell(char="Y"))

    assert buf.get(0, 0).char == "X"
    assert clone.get(0, 0).char == "Y"
