# tests/test_ui_layout.py
from flow.layout.compute import compute_layout
from flow.layout.types import Size
from flow.ui.layout import Box, Flex


class TestFlexElement:
    def test_flex_context_manager(self):
        """Flex works as context manager."""
        with Flex(direction="row", width=200, height=100) as container:
            with Box(flex_grow=1):
                pass
            with Box(flex_grow=1):
                pass

        assert len(container.children) == 2

    def test_flex_computes_layout(self):
        """Flex element can compute layout."""
        with Flex(direction="row", width=200, height=100) as root:
            with Box(flex_grow=1):
                pass
            with Box(flex_grow=1):
                pass

        # Compute layout
        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=200, height=100))

        # Verify computed positions
        assert layout_node.children[0].layout.width == 100
        assert layout_node.children[1].layout.x == 100

    def test_flex_with_gap(self):
        """Flex element supports gap property."""
        with Flex(direction="row", width=200, height=100, gap=20) as root:
            with Box(flex_grow=1):
                pass
            with Box(flex_grow=1):
                pass

        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=200, height=100))

        # 200 - 20 gap = 180, split = 90 each
        assert layout_node.children[0].layout.width == 90
        assert layout_node.children[1].layout.width == 90
        assert layout_node.children[1].layout.x == 110  # 90 + 20 gap

    def test_flex_column_direction(self):
        """Flex can stack items vertically."""
        with Flex(direction="column", width=100, height=200) as root:
            with Box(flex_grow=1):
                pass
            with Box(flex_grow=1):
                pass

        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=100, height=200))

        assert layout_node.children[0].layout.height == 100
        assert layout_node.children[1].layout.height == 100
        assert layout_node.children[1].layout.y == 100


class TestBoxElement:
    def test_box_with_fixed_size(self):
        """Box with fixed dimensions."""
        box = Box(width=50, height=50)
        style = box.get_layout_style()

        assert style.width.resolve(100) == 50
        assert style.height.resolve(100) == 50

    def test_box_with_flex_grow(self):
        """Box with flex-grow fills available space."""
        box = Box(flex_grow=1)
        style = box.get_layout_style()

        assert style.flex_grow == 1.0

    def test_box_default_flex_shrink(self):
        """Box has default flex-shrink of 1."""
        box = Box()
        style = box.get_layout_style()

        assert style.flex_shrink == 1.0

    def test_box_percent_width(self):
        """Box supports percentage dimensions."""
        box = Box(width="50%", height="100%")
        style = box.get_layout_style()

        assert style.width.resolve(200) == 100
        assert style.height.resolve(100) == 100
