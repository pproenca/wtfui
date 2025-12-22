# tests/test_console_buffer.py
"""Tests for console Buffer - the terminal framebuffer."""

from wtfui.tui.renderer.buffer import Buffer
from wtfui.tui.renderer.cell import Cell


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


class TestBufferCloneOptimization:
    """Tests for optimized Buffer.clone() - shallow copy instead of deep."""

    def test_clone_creates_independent_cell_list(self):
        """Cloned buffer should have separate list, same Cell references."""
        buf1 = Buffer(10, 2)
        buf1.set(0, 0, Cell(char="A"))

        buf2 = buf1.clone()

        # Lists should be different objects
        assert buf2._cells is not buf1._cells

    def test_clone_shares_cell_objects_initially(self):
        """Shallow copy: cells are shared until modified."""
        buf1 = Buffer(10, 2)
        buf1.set(0, 0, Cell(char="A"))

        buf2 = buf1.clone()

        # Cell objects should be shared (shallow copy)
        idx = buf1._index(0, 0)
        assert buf2._cells[idx] is buf1._cells[idx]

    def test_clone_modifications_are_independent(self):
        """Modifying cloned buffer should not affect original."""
        buf1 = Buffer(10, 2)
        buf1.set(0, 0, Cell(char="A"))

        buf2 = buf1.clone()
        buf2.set(0, 0, Cell(char="B"))  # Replace cell at index

        assert buf1.get(0, 0).char == "A"
        assert buf2.get(0, 0).char == "B"

    def test_clone_is_shallow_copy(self):
        """Verify clone uses list() shallow copy, not list comprehension."""
        buf1 = Buffer(80, 24)  # 1920 cells

        buf2 = buf1.clone()

        # All cells should be same objects (shallow copy)
        for i in range(len(buf1._cells)):
            assert buf2._cells[i] is buf1._cells[i]


def test_cell_reset_to_defaults():
    """Cell.reset() should restore all fields to default values."""
    from wtfui.tui.renderer.cell import Cell

    cell = Cell(
        char="X", fg=(255, 0, 0), bg=(0, 255, 0), bold=True, dim=True, italic=True, underline=True
    )
    cell.reset()

    assert cell.char == " "
    assert cell.fg is None
    assert cell.bg is None
    assert cell.bold is False
    assert cell.dim is False
    assert cell.italic is False
    assert cell.underline is False


def test_buffer_clear_mutates_cloned_cells():
    """clear() resets cells in-place, which affects shallow clones.

    With the buffer swap optimization (swapping references instead of
    cloning after flush), the renderer never shares cells between buffers.
    This allows clear() to reset in-place for performance.

    This test documents that clone() + clear() will affect both buffers
    since they share Cell objects. Callers should use buffer swapping
    (as ConsoleRenderer.flush() does) instead of clone() + clear().
    """
    buf1 = Buffer(width=10, height=2)
    buf1.set(0, 0, Cell(char="X"))

    buf2 = buf1.clone()  # Shallow copy shares cells
    buf1.clear()  # Resets cells in-place

    # Clone is affected because cells are shared (shallow copy)
    assert buf2.get(0, 0).char == " ", "Clone affected by in-place reset"


def test_clear_reuses_cell_objects():
    """Verify clear() resets cells in-place instead of reallocating."""
    buf = Buffer(10, 10)

    # Modify some cells directly (not via set() which replaces)
    buf._cells[0].char = "X"
    buf._cells[0].bold = True
    buf._cells[50].char = "Y"
    buf._cells[50].fg = (255, 0, 0)

    # Get references AFTER modification (these are the cells we expect to keep)
    ids_before_clear = [id(c) for c in buf._cells]

    # Clear should reset in-place
    buf.clear()

    # Same cell objects should be reused (not reallocated)
    ids_after_clear = [id(c) for c in buf._cells]
    assert ids_after_clear == ids_before_clear, "clear() should reuse existing Cell objects"

    # All cells should be reset to defaults
    for cell in buf._cells:
        assert cell.char == " "
        assert cell.fg is None
        assert cell.bg is None
        assert cell.bold is False
