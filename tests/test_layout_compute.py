# tests/test_layout_compute.py
from flow.layout.compute import compute_layout
from flow.layout.node import LayoutNode
from flow.layout.style import FlexDirection, FlexStyle, JustifyContent
from flow.layout.types import Dimension, Size


class TestComputeLayout:
    def test_single_node_fixed_size(self):
        """Single node with fixed dimensions."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            )
        )

        compute_layout(node, available=Size(width=500, height=500))

        assert node.layout.width == 100
        assert node.layout.height == 50
        assert node.layout.x == 0
        assert node.layout.y == 0

    def test_row_layout(self):
        """Basic row layout with flex-grow."""
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(child1)
        root.add_child(child2)

        compute_layout(root, available=Size(width=200, height=100))

        # Children split the 200px width
        assert child1.layout.width == 100
        assert child2.layout.width == 100
        assert child1.layout.x == 0
        assert child2.layout.x == 100

    def test_column_layout(self):
        """Column layout stacks vertically."""
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(200),
                flex_direction=FlexDirection.COLUMN,
            )
        )
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(child1)
        root.add_child(child2)

        compute_layout(root, available=Size(width=100, height=200))

        assert child1.layout.height == 100
        assert child2.layout.height == 100
        assert child1.layout.y == 0
        assert child2.layout.y == 100

    def test_justify_center(self):
        """Justify content center."""
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                justify_content=JustifyContent.CENTER,
            )
        )
        child = LayoutNode(style=FlexStyle(width=Dimension.points(50), height=Dimension.points(50)))

        root.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # Child centered: (200 - 50) / 2 = 75
        assert child.layout.x == 75

    def test_nested_layout(self):
        """Nested flex containers."""
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(300),
                height=Dimension.points(200),
                flex_direction=FlexDirection.ROW,
            )
        )
        left = LayoutNode(style=FlexStyle(flex_grow=1.0))
        right = LayoutNode(style=FlexStyle(flex_grow=1.0, flex_direction=FlexDirection.COLUMN))
        right_top = LayoutNode(style=FlexStyle(flex_grow=1.0))
        right_bottom = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(left)
        root.add_child(right)
        right.add_child(right_top)
        right.add_child(right_bottom)

        compute_layout(root, available=Size(width=300, height=200))

        # Left and right split 300px
        assert left.layout.width == 150
        assert right.layout.width == 150
        assert right.layout.x == 150

        # Right's children split 200px height
        assert right_top.layout.height == 100
        assert right_bottom.layout.height == 100
        assert right_bottom.layout.y == 100

    def test_no_children(self):
        """Node without children gets its own size only."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            )
        )

        compute_layout(node, available=Size(width=500, height=500))

        assert node.layout.width == 100
        assert node.layout.height == 50

    def test_dirty_flag_cleared(self):
        """compute_layout clears the dirty flag."""
        node = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        assert node.is_dirty()

        compute_layout(node, available=Size(width=500, height=500))

        assert not node.is_dirty()
