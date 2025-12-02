# tests/test_console_theme.py
"""Tests for console theme and color palette."""

from flow.renderer.console.cell import Cell
from flow.renderer.console.theme import PALETTE, apply_cls_to_cell


def test_palette_has_tailwind_colors():
    """Palette includes standard Tailwind colors."""
    assert "red-500" in PALETTE
    assert "blue-600" in PALETTE
    assert "slate-900" in PALETTE
    assert "green-400" in PALETTE


def test_palette_colors_are_rgb_tuples():
    """All palette values are RGB tuples."""
    for name, color in PALETTE.items():
        assert isinstance(color, tuple), f"{name} should be tuple"
        assert len(color) == 3, f"{name} should have 3 components"
        assert all(0 <= c <= 255 for c in color), f"{name} should be 0-255"


def test_apply_bg_class():
    """Apply background color class."""
    cell = Cell()
    apply_cls_to_cell(cell, "bg-red-500")
    assert cell.bg == PALETTE["red-500"]


def test_apply_text_class():
    """Apply text (foreground) color class."""
    cell = Cell()
    apply_cls_to_cell(cell, "text-blue-600")
    assert cell.fg == PALETTE["blue-600"]


def test_apply_bold_class():
    """Apply bold class."""
    cell = Cell()
    apply_cls_to_cell(cell, "bold")
    assert cell.bold is True


def test_apply_multiple_classes():
    """Apply multiple classes at once."""
    cell = Cell()
    apply_cls_to_cell(cell, "bg-slate-900 text-green-400 bold")
    assert cell.bg == PALETTE["slate-900"]
    assert cell.fg == PALETTE["green-400"]
    assert cell.bold is True


def test_unknown_class_ignored():
    """Unknown classes are silently ignored."""
    cell = Cell()
    apply_cls_to_cell(cell, "unknown-class bg-red-500")
    # Should not raise, and should apply known class
    assert cell.bg == PALETTE["red-500"]
