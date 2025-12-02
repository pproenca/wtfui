# tests/test_layout_aspect_ratio.py
from flow.layout.compute import compute_layout
from flow.layout.node import LayoutNode
from flow.layout.style import FlexDirection, FlexStyle
from flow.layout.types import Dimension, Size


class TestAspectRatio:
    def test_aspect_ratio_calculates_height_from_width(self):
        """When width is set, height is calculated from aspect ratio."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                aspect_ratio=2.0,  # width:height = 2:1
            )
        )

        compute_layout(node, Size(width=300, height=300))

        assert node.layout.width == 200
        assert node.layout.height == 100  # 200 / 2 = 100

    def test_aspect_ratio_calculates_width_from_height(self):
        """When height is set, width is calculated from aspect ratio."""
        node = LayoutNode(
            style=FlexStyle(
                height=Dimension.points(100),
                aspect_ratio=2.0,  # width:height = 2:1
            )
        )

        compute_layout(node, Size(width=300, height=300))

        assert node.layout.width == 200  # 100 * 2 = 200
        assert node.layout.height == 100

    def test_aspect_ratio_respects_max_width(self):
        """Aspect ratio respects max_width constraint."""
        node = LayoutNode(
            style=FlexStyle(
                height=Dimension.points(100),
                aspect_ratio=2.0,  # Would want width=200
                max_width=Dimension.points(150),
            )
        )

        compute_layout(node, Size(width=300, height=300))

        assert node.layout.width == 150  # Clamped by max_width
        assert node.layout.height == 100

    def test_aspect_ratio_respects_max_height(self):
        """Aspect ratio respects max_height constraint."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                aspect_ratio=2.0,  # Would want height=100
                max_height=Dimension.points(50),
            )
        )

        compute_layout(node, Size(width=300, height=300))

        assert node.layout.width == 200
        assert node.layout.height == 50  # Clamped by max_height

    def test_aspect_ratio_with_flex_grow(self):
        """Aspect ratio works with flex children that grow."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))

        # Child grows to fill parent, then height is calculated from aspect ratio
        child = LayoutNode(
            style=FlexStyle(
                flex_grow=1,
                aspect_ratio=2.0,
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(width=200, height=300))

        assert child.layout.width == 200  # Fills parent
        assert child.layout.height == 100  # 200 / 2

    def test_aspect_ratio_square(self):
        """Aspect ratio 1.0 creates a square."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                aspect_ratio=1.0,
            )
        )

        compute_layout(node, Size(width=200, height=200))

        assert node.layout.width == 100
        assert node.layout.height == 100

    def test_no_aspect_ratio(self):
        """Without aspect ratio, dimensions are independent."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
                aspect_ratio=None,
            )
        )

        compute_layout(node, Size(width=200, height=200))

        assert node.layout.width == 100
        assert node.layout.height == 50  # Independent

    def test_aspect_ratio_with_percent_width(self):
        """Aspect ratio works with percentage width."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.percent(50),  # 50% of 200 = 100
                aspect_ratio=0.5,  # width:height = 1:2
            )
        )

        compute_layout(node, Size(width=200, height=300))

        assert node.layout.width == 100
        assert node.layout.height == 200  # 100 / 0.5 = 200
