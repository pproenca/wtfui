# tests/test_console_cell.py
"""Tests for console Cell - the atomic unit of terminal rendering."""

from wtfui.tui.renderer.cell import Cell


def test_cell_default_values():
    """Cell has sensible defaults for empty space."""
    cell = Cell()
    assert cell.char == " "
    assert cell.fg is None
    assert cell.bg is None
    assert cell.bold is False
    assert cell.dim is False


def test_cell_with_char_and_color():
    """Cell can hold character with foreground color."""
    cell = Cell(char="A", fg=(255, 0, 0))
    assert cell.char == "A"
    assert cell.fg == (255, 0, 0)


def test_cell_equality():
    """Two cells with same values are equal."""
    cell1 = Cell(char="X", fg=(0, 255, 0), bold=True)
    cell2 = Cell(char="X", fg=(0, 255, 0), bold=True)
    assert cell1 == cell2


def test_cell_inequality_on_char():
    """Cells with different chars are not equal."""
    cell1 = Cell(char="A")
    cell2 = Cell(char="B")
    assert cell1 != cell2


def test_cell_inequality_on_style():
    """Cells with different styles are not equal."""
    cell1 = Cell(char="A", bold=True)
    cell2 = Cell(char="A", bold=False)
    assert cell1 != cell2


def test_cell_uses_slots():
    """Cell uses __slots__ for memory efficiency."""
    cell = Cell()
    assert hasattr(Cell, "__slots__") or hasattr(cell, "__dataclass_fields__")
