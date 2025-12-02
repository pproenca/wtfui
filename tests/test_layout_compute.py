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


class TestComputeLayoutBorder:
    """Tests for border support in compute_layout (Task 2.3)."""

    def test_border_reduces_inner_content_area_row(self):
        """Border should reduce available space for children in row layout."""
        from flow.layout.types import Border

        # Container: 200x100, border: 10px all sides
        # Inner area should be: (200 - 20) x (100 - 20) = 180 x 80
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                border=Border.all(10.0),
            )
        )
        child = LayoutNode(style=FlexStyle(flex_grow=1.0))
        root.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # Child should fill inner area (minus border)
        assert child.layout.width == 180  # 200 - (10 + 10)
        assert child.layout.height == 80  # 100 - (10 + 10)

    def test_border_offsets_children_position_row(self):
        """Children should be offset by border + padding in row layout."""
        from flow.layout.types import Border, Spacing

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                border=Border(top=5.0, right=10.0, bottom=15.0, left=20.0),
                padding=Spacing.all(Dimension.points(10.0)),
            )
        )
        child = LayoutNode(style=FlexStyle(width=Dimension.points(50), height=Dimension.points(30)))
        root.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # Child should be offset by border.left + padding.left
        assert child.layout.x == 30  # border.left (20) + padding.left (10)
        # Child should be offset by border.top + padding.top
        assert child.layout.y == 15  # border.top (5) + padding.top (10)

    def test_border_reduces_inner_content_area_column(self):
        """Border should reduce available space for children in column layout."""
        from flow.layout.types import Border

        # Container: 100x200, border: 10px all sides
        # Inner area should be: (100 - 20) x (200 - 20) = 80 x 180
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(200),
                flex_direction=FlexDirection.COLUMN,
                border=Border.all(10.0),
            )
        )
        child = LayoutNode(style=FlexStyle(flex_grow=1.0))
        root.add_child(child)

        compute_layout(root, available=Size(width=100, height=200))

        # Child should fill inner area (minus border)
        assert child.layout.width == 80  # 100 - (10 + 10)
        assert child.layout.height == 180  # 200 - (10 + 10)

    def test_border_offsets_children_position_column(self):
        """Children should be offset by border + padding in column layout."""
        from flow.layout.types import Border, Spacing

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(200),
                flex_direction=FlexDirection.COLUMN,
                border=Border(top=8.0, right=6.0, bottom=4.0, left=12.0),
                padding=Spacing.all(Dimension.points(5.0)),
            )
        )
        child = LayoutNode(style=FlexStyle(width=Dimension.points(30), height=Dimension.points(50)))
        root.add_child(child)

        compute_layout(root, available=Size(width=100, height=200))

        # Child should be offset by border.left + padding.left
        assert child.layout.x == 17  # border.left (12) + padding.left (5)
        # Child should be offset by border.top + padding.top
        assert child.layout.y == 13  # border.top (8) + padding.top (5)

    def test_border_with_multiple_children_row(self):
        """Border should work correctly with multiple children in row layout."""
        from flow.layout.types import Border

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(220),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                border=Border.all(10.0),
            )
        )
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        root.add_child(child1)
        root.add_child(child2)

        compute_layout(root, available=Size(width=220, height=100))

        # Inner width: 220 - 20 = 200, split between two children
        assert child1.layout.width == 100
        assert child2.layout.width == 100
        # First child starts at border.left
        assert child1.layout.x == 10
        # Second child follows first
        assert child2.layout.x == 110
        # Both offset by border.top
        assert child1.layout.y == 10
        assert child2.layout.y == 10

    def test_border_with_zero_values(self):
        """Zero border should behave the same as no border."""
        from flow.layout.types import Border

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                border=Border.zero(),
            )
        )
        child = LayoutNode(style=FlexStyle(flex_grow=1.0))
        root.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # No border, child fills entire container
        assert child.layout.width == 200
        assert child.layout.height == 100
        assert child.layout.x == 0
        assert child.layout.y == 0

    def test_border_with_asymmetric_values(self):
        """Border with different values per side should work correctly."""
        from flow.layout.types import Border

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                border=Border(top=2.0, right=4.0, bottom=6.0, left=8.0),
            )
        )
        child = LayoutNode(style=FlexStyle(flex_grow=1.0))
        root.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # Inner width: 200 - (8 + 4) = 188
        assert child.layout.width == 188
        # Inner height: 100 - (2 + 6) = 92
        assert child.layout.height == 92
        # Offset by border.left and border.top
        assert child.layout.x == 8
        assert child.layout.y == 2
