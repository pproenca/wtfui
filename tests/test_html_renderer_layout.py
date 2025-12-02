# tests/test_html_renderer_layout.py
from flow.layout.compute import compute_layout
from flow.layout.types import Size
from flow.renderer.html import HTMLRenderer
from flow.ui.layout import Box, Flex


class TestHTMLRendererLayout:
    def test_render_with_layout_produces_absolute_css(self):
        """HTMLRenderer produces absolute positioning CSS from layout."""
        with Flex(direction="row", width=200, height=100) as root, Box(flex_grow=1):
            pass

        # Compute layout
        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=200, height=100))

        # Render with layout
        renderer = HTMLRenderer()
        html = renderer.render_with_layout(root, layout_node)

        # Check style attributes in HTML
        assert 'style="' in html
        assert "position: absolute" in html

    def test_style_dict_to_css_string(self):
        """Style dict is converted to CSS string."""
        with Flex(direction="row", width=100, height=50) as root:
            pass

        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=100, height=50))

        renderer = HTMLRenderer()
        html = renderer.render_with_layout(root, layout_node)

        # Should have pixel dimensions
        assert "width: 100px" in html
        assert "height: 50px" in html
        assert "top: 0px" in html
        assert "left: 0px" in html

    def test_layout_container_with_overflow(self):
        """Layout container supports overflow styling."""
        with (
            Flex(
                direction="row",
                width=200,
                height=100,
                style={"overflow": "hidden"},
            ) as root,
            Box(flex_grow=1),
        ):
            pass

        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=200, height=100))

        renderer = HTMLRenderer()
        html = renderer.render_with_layout(root, layout_node)

        # Original overflow style should be preserved
        assert "overflow: hidden" in html

    def test_nested_layout_rendering(self):
        """Nested elements get correct absolute positions."""
        with Flex(direction="row", width=200, height=100) as root:
            with Box(flex_grow=1):
                pass
            with Box(flex_grow=1):
                pass

        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=200, height=100))

        renderer = HTMLRenderer()
        html = renderer.render_with_layout(root, layout_node)

        # First child at left: 0px, second at left: 100px
        assert "left: 0px" in html
        assert "left: 100px" in html

    def test_render_without_layout_unchanged(self):
        """Regular render() method still works without layout."""
        with Flex(direction="row", width=200, height=100) as root, Box(flex_grow=1):
            pass

        renderer = HTMLRenderer()
        html = renderer.render(root)

        # Should not have position: absolute when rendered without layout
        assert "position: absolute" not in html

    def test_layout_tag_mapping(self):
        """Layout elements use correct HTML tags."""
        with Flex(direction="row", width=100, height=50) as root, Box(flex_grow=1):
            pass

        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=100, height=50))

        renderer = HTMLRenderer()
        html = renderer.render_with_layout(root, layout_node)

        # Flex and Box should render as div
        assert html.count("<div") >= 2  # root + child
