# tests/test_element_render_node.py
"""Tests for RenderTreeBuilder with Tailwind conflict resolution."""

from wtfui.core.element import Element
from wtfui.tui.builder import RenderTreeBuilder


class TestRenderNodeTailwindConflict:
    """Tailwind classes stripped when explicit props conflict."""

    def test_width_prop_strips_tailwind_width_class(self):
        """Explicit width prop removes w-* Tailwind classes."""
        el = Element(tag="div", class_="w-10 bg-blue-500", width=100)
        node = RenderTreeBuilder().build(el)

        # class_ should have w-10 stripped, bg-blue-500 preserved
        assert "w-10" not in node.props.get("class_", "")
        assert "bg-blue-500" in node.props.get("class_", "")

    def test_no_stripping_without_explicit_props(self):
        """Tailwind classes preserved when no explicit props conflict."""
        el = Element(tag="div", class_="w-10 h-10 bg-red-500")
        node = RenderTreeBuilder().build(el)

        # All classes preserved
        class_str = node.props.get("class_", "")
        assert "w-10" in class_str
        assert "h-10" in class_str
        assert "bg-red-500" in class_str

    def test_multiple_conflicts_stripped(self):
        """Multiple conflicting Tailwind classes stripped."""
        el = Element(
            tag="div",
            class_="w-full h-screen flex-row justify-center p-4",
            width=200,
            height=100,
            flex_direction="row",
            justify_content="center",
        )
        node = RenderTreeBuilder().build(el)

        class_str = node.props.get("class_", "")
        # Geometry classes stripped
        assert "w-full" not in class_str
        assert "h-screen" not in class_str
        assert "flex-row" not in class_str
        assert "justify-center" not in class_str
        # Non-geometry preserved
        assert "p-4" in class_str
