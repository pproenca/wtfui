# tests/test_layout_direction.py
"""Tests for direction resolution (RTL/LTR support)."""

from flow.layout.direction import resolve_flex_direction
from flow.layout.style import Direction, FlexDirection


class TestResolveFlexDirection:
    """Test resolve_flex_direction for RTL/LTR support."""

    def test_row_ltr_unchanged(self):
        """Row in LTR stays row."""
        result = resolve_flex_direction(FlexDirection.ROW, Direction.LTR)
        assert result == FlexDirection.ROW

    def test_row_rtl_becomes_row_reverse(self):
        """Row in RTL becomes row-reverse."""
        result = resolve_flex_direction(FlexDirection.ROW, Direction.RTL)
        assert result == FlexDirection.ROW_REVERSE

    def test_row_reverse_ltr_unchanged(self):
        """Row-reverse in LTR stays row-reverse."""
        result = resolve_flex_direction(FlexDirection.ROW_REVERSE, Direction.LTR)
        assert result == FlexDirection.ROW_REVERSE

    def test_row_reverse_rtl_becomes_row(self):
        """Row-reverse in RTL becomes row."""
        result = resolve_flex_direction(FlexDirection.ROW_REVERSE, Direction.RTL)
        assert result == FlexDirection.ROW

    def test_column_ltr_unchanged(self):
        """Column is not affected by LTR."""
        result = resolve_flex_direction(FlexDirection.COLUMN, Direction.LTR)
        assert result == FlexDirection.COLUMN

    def test_column_rtl_unchanged(self):
        """Column is not affected by RTL."""
        result = resolve_flex_direction(FlexDirection.COLUMN, Direction.RTL)
        assert result == FlexDirection.COLUMN

    def test_column_reverse_ltr_unchanged(self):
        """Column-reverse is not affected by LTR."""
        result = resolve_flex_direction(FlexDirection.COLUMN_REVERSE, Direction.LTR)
        assert result == FlexDirection.COLUMN_REVERSE

    def test_column_reverse_rtl_unchanged(self):
        """Column-reverse is not affected by RTL."""
        result = resolve_flex_direction(FlexDirection.COLUMN_REVERSE, Direction.RTL)
        assert result == FlexDirection.COLUMN_REVERSE

    def test_inherit_direction_unchanged(self):
        """INHERIT direction doesn't affect flex direction."""
        result = resolve_flex_direction(FlexDirection.ROW, Direction.INHERIT)
        assert result == FlexDirection.ROW
