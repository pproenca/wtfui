# tests/test_render_layout.py
"""Tests for render layout integration.

After the performance optimization, build_with_layout passes
LayoutResult directly via RenderNode.layout instead of CSS strings in style dict.
"""

from wtfui.tui.adapter import LayoutAdapter
from wtfui.tui.builder import RenderTreeBuilder
from wtfui.tui.layout.compute import compute_layout
from wtfui.tui.layout.types import Size
from wtfui.ui.layout import Box, Flex


class TestRenderWithLayout:
    def test_computed_layout_in_render(self):
        """RenderNode includes computed layout in layout field."""
        with Flex(direction="row", width=200, height=100) as root:
            Box(flex_grow=1, cls="left")
            Box(flex_grow=1, cls="right")

        # Compute layout
        layout_node = LayoutAdapter().to_layout_node(root)
        compute_layout(layout_node, Size(width=200, height=100))

        # Convert to RenderNode with computed styles
        render_node = RenderTreeBuilder().build_with_layout(root, layout_node)

        # Verify computed positions are in layout field (not style dict)
        left_layout = render_node.children[0].layout
        assert left_layout is not None
        assert left_layout.x == 0
        assert left_layout.width == 100

        right_layout = render_node.children[1].layout
        assert right_layout is not None
        assert right_layout.x == 100

    def test_layout_style_includes_all_dimensions(self):
        """Layout includes position and dimensions."""
        with Flex(direction="column", width=100, height=200) as root:
            Box(flex_grow=1)

        layout_node = LayoutAdapter().to_layout_node(root)
        compute_layout(layout_node, Size(width=100, height=200))

        render_node = RenderTreeBuilder().build_with_layout(root, layout_node)
        child_layout = render_node.children[0].layout

        assert child_layout is not None
        assert child_layout.y == 0
        assert child_layout.x == 0
        assert child_layout.width == 100
        assert child_layout.height == 200

    def test_nested_layout_rendering(self):
        """Nested containers get correct computed layout."""
        with Flex(direction="row", width=200, height=100) as root:
            with Flex(direction="column", flex_grow=1):
                Box(flex_grow=1)
            Box(flex_grow=1)

        layout_node = LayoutAdapter().to_layout_node(root)
        compute_layout(layout_node, Size(width=200, height=100))

        render_node = RenderTreeBuilder().build_with_layout(root, layout_node)

        # Left container
        left_layout = render_node.children[0].layout
        assert left_layout is not None
        assert left_layout.width == 100

        # Nested child in left container
        nested_layout = render_node.children[0].children[0].layout
        assert nested_layout is not None
        assert nested_layout.height == 100

    def test_render_node_without_layout(self):
        """RenderTreeBuilder.build still works without layout."""
        with Flex(direction="row", width=200, height=100) as root:
            Box(flex_grow=1)

        # Regular render (without layout)
        render_node = RenderTreeBuilder().build(root)

        # Should have layout=None when not computed
        assert render_node.children[0].layout is None
