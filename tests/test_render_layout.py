# tests/test_render_layout.py
from flow.layout.compute import compute_layout
from flow.layout.types import Size
from flow.ui.layout import Box, Flex


class TestRenderWithLayout:
    def test_computed_layout_in_render(self):
        """RenderNode includes computed layout as style."""
        with Flex(direction="row", width=200, height=100) as root:
            with Box(flex_grow=1, cls="left"):
                pass
            with Box(flex_grow=1, cls="right"):
                pass

        # Compute layout
        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=200, height=100))

        # Convert to RenderNode with computed styles
        render_node = root.to_render_node_with_layout(layout_node)

        # Verify computed positions are in style
        left_style = render_node.children[0].props.get("style", {})
        assert left_style.get("left") == "0px"
        assert left_style.get("width") == "100px"

        right_style = render_node.children[1].props.get("style", {})
        assert right_style.get("left") == "100px"

    def test_layout_style_includes_all_dimensions(self):
        """Layout style includes position and dimensions."""
        with Flex(direction="column", width=100, height=200) as root, Box(flex_grow=1):
            pass

        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=100, height=200))

        render_node = root.to_render_node_with_layout(layout_node)
        child_style = render_node.children[0].props.get("style", {})

        assert child_style.get("top") == "0px"
        assert child_style.get("left") == "0px"
        assert child_style.get("width") == "100px"
        assert child_style.get("height") == "200px"

    def test_nested_layout_rendering(self):
        """Nested containers get correct computed layout."""
        with Flex(direction="row", width=200, height=100) as root:
            with Flex(direction="column", flex_grow=1), Box(flex_grow=1):
                pass
            with Box(flex_grow=1):
                pass

        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=200, height=100))

        render_node = root.to_render_node_with_layout(layout_node)

        # Left container
        left_style = render_node.children[0].props.get("style", {})
        assert left_style.get("width") == "100px"

        # Nested child in left container
        nested_style = render_node.children[0].children[0].props.get("style", {})
        assert nested_style.get("height") == "100px"

    def test_render_node_without_layout(self):
        """to_render_node still works without layout."""
        with Flex(direction="row", width=200, height=100) as root, Box(flex_grow=1):
            pass

        # Regular render (without layout)
        render_node = root.to_render_node()

        # Should not have style with layout positions
        child_props = render_node.children[0].props
        assert "style" not in child_props or "left" not in child_props.get("style", {})
