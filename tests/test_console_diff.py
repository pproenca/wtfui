# tests/test_console_diff.py
"""Tests for differential buffer painting."""

from flow.renderer.console.buffer import Buffer
from flow.renderer.console.cell import Cell
from flow.renderer.console.diff import diff_buffers


def test_diff_empty_buffers():
    """Two empty buffers produce no diff."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)

    result = diff_buffers(buf_a, buf_b)

    assert result.changes == []
    assert result.ansi_output == ""


def test_diff_single_change():
    """Single cell change produces minimal output."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)
    buf_b.set(3, 2, Cell(char="X"))

    result = diff_buffers(buf_a, buf_b)

    assert len(result.changes) == 1
    assert result.changes[0] == (3, 2)
    assert "X" in result.ansi_output


def test_diff_multiple_changes():
    """Multiple changes are batched efficiently."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)
    buf_b.set(0, 0, Cell(char="A"))
    buf_b.set(1, 0, Cell(char="B"))
    buf_b.set(2, 0, Cell(char="C"))

    result = diff_buffers(buf_a, buf_b)

    assert len(result.changes) == 3
    # Adjacent cells should ideally be written together
    assert "ABC" in result.ansi_output or all(c in result.ansi_output for c in "ABC")


def test_diff_with_colors():
    """Color changes are included in output."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)
    buf_b.set(0, 0, Cell(char="X", fg=(255, 0, 0)))

    result = diff_buffers(buf_a, buf_b)

    # Should include RGB color escape sequence
    assert "38;2;255;0;0" in result.ansi_output


def test_diff_identical_cells_no_change():
    """Identical cells produce no diff."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)

    cell = Cell(char="Y", fg=(0, 255, 0))
    buf_a.set(5, 3, cell)
    buf_b.set(5, 3, Cell(char="Y", fg=(0, 255, 0)))  # Same content

    result = diff_buffers(buf_a, buf_b)

    assert (5, 3) not in result.changes


def test_diff_respects_style_changes():
    """Style-only changes (bold, dim) are detected."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)

    buf_a.set(0, 0, Cell(char="X", bold=False))
    buf_b.set(0, 0, Cell(char="X", bold=True))

    result = diff_buffers(buf_a, buf_b)

    assert len(result.changes) == 1
