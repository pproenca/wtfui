# tests/renderer/console/test_theme.py
"""Tests for console theme, color palette, and style application."""

from wtfui.core.style import Style
from wtfui.tui.renderer.cell import Cell
from wtfui.tui.renderer.theme import PALETTE, apply_cls_to_cell, apply_style_to_cell

# --- Tailwind Palette Tests ---


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


# --- Class String Application (apply_cls_to_cell) ---


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


# --- Style Object Application (apply_style_to_cell) ---


class TestApplyStyleToCell:
    """Test Style object application to Cell."""

    def test_apply_color(self):
        """Style.color should set cell foreground."""
        cell = Cell(char="X")
        style = Style(color="red-500")

        apply_style_to_cell(cell, style)

        assert cell.fg == (239, 68, 68)  # Tailwind red-500

    def test_apply_bg(self):
        """Style.bg should set cell background."""
        cell = Cell(char="X")
        style = Style(bg="slate-800")

        apply_style_to_cell(cell, style)

        assert cell.bg == (30, 41, 59)  # Tailwind slate-800

    def test_apply_bold(self):
        """Style.font_weight='bold' should set cell.bold."""
        cell = Cell(char="X")
        style = Style(font_weight="bold")

        apply_style_to_cell(cell, style)

        assert cell.bold is True

    def test_apply_underline(self):
        """Style.text_decoration='underline' should set cell.underline."""
        cell = Cell(char="X")
        style = Style(text_decoration="underline")

        apply_style_to_cell(cell, style)

        assert cell.underline is True

    def test_apply_dim_from_opacity(self):
        """Style.opacity < 1.0 should set cell.dim."""
        cell = Cell(char="X")
        style = Style(opacity=0.5)

        apply_style_to_cell(cell, style)

        assert cell.dim is True

    def test_hex_color_parsing(self):
        """Style with hex color should work."""
        cell = Cell(char="X")
        style = Style(color="#ff5500")

        apply_style_to_cell(cell, style)

        assert cell.fg == (255, 85, 0)
