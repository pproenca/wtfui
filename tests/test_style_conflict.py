# tests/test_style_conflict.py
"""Tests for style vs prop conflict resolution (Amendment Beta)."""

from wtfui.tui.layout.style_resolver import (
    GEOMETRY_CLASS_PATTERNS,
    strip_geometry_classes,
)


class TestGeometryClassStripping:
    """Amendment Beta: Explicit Layout Props define the Truth."""

    def test_strip_width_classes(self):
        """Width classes are stripped when width prop is present."""
        cls = "w-10 bg-blue-500 text-white"
        result = strip_geometry_classes(cls, has_width=True)
        assert result == "bg-blue-500 text-white"

    def test_strip_height_classes(self):
        """Height classes are stripped when height prop is present."""
        cls = "h-20 h-screen bg-red-500"
        result = strip_geometry_classes(cls, has_height=True)
        assert result == "bg-red-500"

    def test_strip_flex_classes(self):
        """Flex classes stripped when flex props present."""
        cls = "flex flex-row justify-center items-start gap-4 p-2"
        result = strip_geometry_classes(
            cls,
            has_flex_direction=True,
            has_justify=True,
            has_align=True,
            has_gap=True,
        )
        assert result == "p-2"  # Only non-geometry class remains

    def test_strip_multiple_geometry_classes(self):
        """Multiple geometry classes are stripped."""
        cls = "w-full h-1/2 min-w-0 max-h-screen flex-1 bg-gray-100"
        result = strip_geometry_classes(
            cls,
            has_width=True,
            has_height=True,
            has_flex_grow=True,
        )
        assert result == "bg-gray-100"

    def test_preserve_non_geometry_classes(self):
        """Non-geometry classes are preserved."""
        cls = "rounded-lg shadow-md hover:bg-blue-600 transition-colors"
        result = strip_geometry_classes(cls, has_width=True)
        # No geometry classes to strip
        assert result == cls

    def test_no_stripping_when_no_props(self):
        """Classes preserved when no explicit props conflict."""
        cls = "w-10 h-10 flex-1"
        result = strip_geometry_classes(cls)
        assert result == cls

    def test_geometry_class_patterns_defined(self):
        """Verify geometry class patterns are defined."""
        assert "width" in GEOMETRY_CLASS_PATTERNS
        assert "height" in GEOMETRY_CLASS_PATTERNS
        assert "flex_direction" in GEOMETRY_CLASS_PATTERNS
        assert "gap" in GEOMETRY_CLASS_PATTERNS
